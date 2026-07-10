#!/usr/bin/env python3
"""
Constraint-aware Rust code generator for PAC crates.

Reads a RegisterInfo JSON file (with access_constraints) and generates
a Rust module that adds compile-time safety via affine witness proofs and
constrained write methods alongside the existing svd2rust-generated code.

Usage:
    python applications/pac_codegen/rust_codegen.py applications/pac_codegen/constraint_test/stm32f405_i2c1.json \
        --peripheral i2c1 --output applications/pac_codegen/generated/i2c1/constraints.rs
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Add the repo root to sys.path so we can import the shared defs.py.
# This file lives at applications/pac_codegen/rust_codegen.py, so the repo
# root is three levels up.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from defs import FieldState, RegisterInfo


@dataclass
class NormalizedConstraint:
    """Conjunctive constraints for one target operation."""

    target_register: str
    target_fields: list[str]
    target_operation: str
    preconditions: list[FieldState]
    datasheet_texts: list[str]


def normalize_constraints(register_info: RegisterInfo) -> list[NormalizedConstraint]:
    """Group constraints by operation and deduplicate predicates deterministically."""
    plans: dict[str, NormalizedConstraint] = {}
    seen_preconditions: dict[str, set[tuple[str, str]]] = {}
    seen_fields: dict[str, set[str]] = {}

    for constraint in register_info.access_constraints:
        operation = constraint.target_operation
        if operation not in plans:
            plans[operation] = NormalizedConstraint(
                target_register=constraint.target_register,
                target_fields=[],
                target_operation=operation,
                preconditions=[],
                datasheet_texts=[],
            )
            seen_preconditions[operation] = set()
            seen_fields[operation] = set()

        plan = plans[operation]
        for field in constraint.target_fields:
            if field not in seen_fields[operation]:
                plan.target_fields.append(field)
                seen_fields[operation].add(field)

        for precondition in constraint.preconditions:
            key = (precondition.field_name, precondition.required_state)
            if key not in seen_preconditions[operation]:
                plan.preconditions.append(precondition)
                seen_preconditions[operation].add(key)

        if constraint.datasheet_text not in plan.datasheet_texts:
            plan.datasheet_texts.append(constraint.datasheet_text)

    return list(plans.values())


def field_to_rust_name(field_name: str) -> str:
    """Map a field name to its svd2rust accessor (lowercase)."""
    return field_name.lower()


def operation_to_proof_name(register_name: str, operation: str) -> str:
    """Generate the private-constructor proof type for an operation."""
    return f"{register_name.capitalize()}{operation.capitalize()}Ready"


def field_to_error_variant(field_name: str, state: str) -> str:
    """Generate an error variant name from field + required state.

    Examples:
        ("STOP", "cleared") -> "StopNotCleared"
        ("START", "set")    -> "StartNotSet"
    """
    name_part = field_name.capitalize()
    if state == "cleared":
        return f"{name_part}NotCleared"
    elif state == "set":
        return f"{name_part}NotSet"
    elif state.startswith("equals:"):
        val = state.split(":", 1)[1]
        return f"{name_part}NotEq{val}"
    else:
        return f"{name_part}Invalid"


def state_to_check(field_name: str, state: str) -> str:
    """Generate a Rust check expression for a field state.

    Returns a string like `r.stop().bit_is_clear()`.
    """
    accessor = field_to_rust_name(field_name)
    if state == "cleared":
        return f"r.{accessor}().bit_is_clear()"
    elif state == "set":
        return f"r.{accessor}().bit_is_set()"
    elif state.startswith("equals:"):
        val = state.split(":", 1)[1]
        return f"r.{accessor}().bits() == {val}"
    else:
        raise ValueError(f"Unknown state: {state}")


def _constraint_doc_lines(
    lines: list[str],
    constraint: NormalizedConstraint,
    indent: str = "",
) -> None:
    lines.append(f"{indent}/// Datasheet constraints:")
    for datasheet_text in constraint.datasheet_texts:
        lines.append(f"{indent}/// - {datasheet_text}")
    if constraint.target_fields:
        fields = ", ".join(constraint.target_fields)
        lines.append(
            f"{indent}/// Target fields: {fields} "
            "(currently enforced at register granularity)."
        )


def _append_verifier(
    lines: list[str],
    constraint: NormalizedConstraint,
    reg_name: str,
) -> None:
    operation = constraint.target_operation
    proof_name = operation_to_proof_name(reg_name, operation)
    lines.append(
        f"    /// Read {reg_name} once and verify every {operation} precondition."
    )
    lines.append("    #[inline(always)]")
    lines.append(
        f"    pub fn verify_{operation}_ready(&self) "
        f"-> Result<{proof_name}, ConstraintError> {{"
    )
    lines.append("        let r = self.reg.read();")
    for precondition in constraint.preconditions:
        error_variant = field_to_error_variant(
            precondition.field_name,
            precondition.required_state,
        )
        check_expr = state_to_check(
            precondition.field_name,
            precondition.required_state,
        )
        lines.append(f"        if !({check_expr}) {{")
        lines.append(
            f"            return Err(ConstraintError::{error_variant});"
        )
        lines.append("        }")
    lines.append(f"        Ok({proof_name}(()))")
    lines.append("    }")
    lines.append("")


def _append_write_methods(
    lines: list[str],
    constraint: NormalizedConstraint,
    reg_name: str,
    reg_spec: str,
) -> None:
    proof_name = operation_to_proof_name(reg_name, "write")
    ux = f"<{reg_spec} as crate::RegisterSpec>::Ux"
    _constraint_doc_lines(lines, constraint, "    ")
    lines.extend(
        [
            "    #[inline(always)]",
            f"    pub fn write_constrained<F>(&self, f: F, _proof: {proof_name}) -> {ux}",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> &mut crate::W<{reg_spec}>,",
            "    {",
            "        self.reg.write(f)",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn write<F>(&self, f: F, proof: {proof_name}) -> {ux}",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> &mut crate::W<{reg_spec}>,",
            "    {",
            "        self.write_constrained(f, proof)",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn reset_constrained(&self, _proof: {proof_name}) {{",
            "        self.reg.reset()",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn reset(&self, proof: {proof_name}) {{",
            "        self.reset_constrained(proof)",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn write_with_zero_constrained<F>(&self, f: F, _proof: {proof_name}) -> {ux}",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> &mut crate::W<{reg_spec}>,",
            "    {",
            "        self.reg.write_with_zero(f)",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn write_with_zero<F>(&self, f: F, proof: {proof_name}) -> {ux}",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> &mut crate::W<{reg_spec}>,",
            "    {",
            "        self.write_with_zero_constrained(f, proof)",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn from_write_constrained<F, T>(&self, f: F, _proof: {proof_name}) -> T",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> T,",
            "    {",
            "        self.reg.from_write(f)",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn from_write<F, T>(&self, f: F, proof: {proof_name}) -> T",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> T,",
            "    {",
            "        self.from_write_constrained(f, proof)",
            "    }",
            "",
        ]
    )


def _append_modify_methods(
    lines: list[str],
    constraint: NormalizedConstraint,
    reg_name: str,
    reg_spec: str,
) -> None:
    proof_name = operation_to_proof_name(reg_name, "modify")
    ux = f"<{reg_spec} as crate::RegisterSpec>::Ux"
    callback = (
        f"for<'w> F: FnOnce(&crate::R<{reg_spec}>, "
        f"&'w mut crate::W<{reg_spec}>) -> &'w mut crate::W<{reg_spec}>,"
    )
    callback_value = (
        f"for<'w> F: FnOnce(&crate::R<{reg_spec}>, "
        f"&'w mut crate::W<{reg_spec}>) -> T,"
    )
    _constraint_doc_lines(lines, constraint, "    ")
    lines.extend(
        [
            "    #[inline(always)]",
            f"    pub fn modify_constrained<F>(&self, f: F, _proof: {proof_name}) -> {ux}",
            "    where",
            f"        {callback}",
            "    {",
            "        self.reg.modify(f)",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn modify<F>(&self, f: F, proof: {proof_name}) -> {ux}",
            "    where",
            f"        {callback}",
            "    {",
            "        self.modify_constrained(f, proof)",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn from_modify_constrained<F, T>(&self, f: F, _proof: {proof_name}) -> T",
            "    where",
            f"        {callback_value}",
            "    {",
            "        self.reg.from_modify(f)",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn from_modify<F, T>(&self, f: F, proof: {proof_name}) -> T",
            "    where",
            f"        {callback_value}",
            "    {",
            "        self.from_modify_constrained(f, proof)",
            "    }",
            "",
        ]
    )


def _append_read_methods(
    lines: list[str],
    constraint: NormalizedConstraint,
    reg_name: str,
    reg_spec: str,
) -> None:
    proof_name = operation_to_proof_name(reg_name, "read")
    reader = f"crate::R<{reg_spec}>"
    _constraint_doc_lines(lines, constraint, "    ")
    lines.extend(
        [
            "    #[inline(always)]",
            f"    pub fn read_constrained(&self, _proof: {proof_name}) -> {reader} {{",
            "        self.reg.read()",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn read(&self, proof: {proof_name}) -> {reader} {{",
            "        self.read_constrained(proof)",
            "    }",
            "",
        ]
    )


def generate_constraint_module(
    register_info: RegisterInfo,
    peripheral: str,
) -> str:
    """Generate operation-specific proof APIs for one constrained register."""
    reg_name = register_info.datasheet_register_abbreviation
    reg_lower = reg_name.lower()
    constraints = normalize_constraints(register_info)
    supported = {"write", "modify", "read"}
    unknown = [
        constraint.target_operation
        for constraint in constraints
        if constraint.target_operation not in supported
    ]
    if unknown:
        raise ValueError(f"Unsupported target operations: {unknown}")
    constraints = [
        constraint for constraint in constraints if constraint.preconditions
    ]

    lines = [
        f"//! Compile-time access constraints for {peripheral.upper()} {reg_name}.",
        "//!",
        "//! Generated from datasheet constraints. Do not edit manually.",
        "//!",
        "//! Each constrained operation requires its own affine composite proof.",
        "",
    ]
    if not constraints:
        lines.append("// No access constraints defined for this register.")
        return "\n".join(lines)

    lines.extend(
        [
            "// === Composite Proofs ===",
            "// Private constructors ensure proofs only come from fresh verification.",
            "",
        ]
    )
    for constraint in constraints:
        operation = constraint.target_operation
        proof_name = operation_to_proof_name(reg_name, operation)
        lines.append(
            f"/// Proof that {reg_name} is ready for a constrained {operation}."
        )
        lines.append(f"pub struct {proof_name}(());")
        lines.append("")

    lines.extend(
        [
            "// === Error Type ===",
            "",
            "/// Errors returned when a precondition is not satisfied.",
            "#[derive(Debug, Clone, Copy, PartialEq, Eq)]",
            "pub enum ConstraintError {",
        ]
    )
    seen_errors: set[str] = set()
    for constraint in constraints:
        for precondition in constraint.preconditions:
            variant = field_to_error_variant(
                precondition.field_name,
                precondition.required_state,
            )
            if variant in seen_errors:
                continue
            seen_errors.add(variant)
            lines.append(
                f"    /// {precondition.field_name} is not "
                f"{precondition.required_state}"
            )
            lines.append(f"    {variant},")
    lines.extend(["}", ""])

    reg_spec = f"super::{reg_lower}::{reg_name}rs"
    lines.append(f"impl crate::ConstrainedReg<{reg_spec}> {{")
    for constraint in constraints:
        _append_verifier(lines, constraint, reg_name)

    lines.extend(
        [
            "    /// Explicitly bypass generated datasheet constraint enforcement.",
            "    ///",
            "    /// # Safety",
            "    /// The caller accepts responsibility for intentionally overriding",
            "    /// the hardware procedure documented by the datasheet.",
            "    #[inline(always)]",
            f"    pub unsafe fn bypass_constraints(&self) -> &crate::Reg<{reg_spec}> {{",
            "        &self.reg",
            "    }",
            "",
        ]
    )

    by_operation = {
        constraint.target_operation: constraint for constraint in constraints
    }
    if "write" in by_operation:
        _append_write_methods(
            lines,
            by_operation["write"],
            reg_name,
            reg_spec,
        )
    if "modify" in by_operation:
        _append_modify_methods(
            lines,
            by_operation["modify"],
            reg_name,
            reg_spec,
        )
    if "read" in by_operation:
        _append_read_methods(
            lines,
            by_operation["read"],
            reg_name,
            reg_spec,
        )
    lines.extend(["}", ""])
    return "\n".join(lines)

def indent_block(text: str, indent: str = "        ") -> str:
    """Indent every line of text by the given prefix."""
    return '\n'.join(
        indent + line if line.strip() else ''
        for line in text.split('\n')
    )


def patch_generic_rs(pac_dir: Path) -> None:
    """Patch generic.rs for constraint module support.

    Changes:
    - Reg.register: private -> pub(crate)
    - raw::R._reg: pub(super) -> pub(crate)
    - raw::W._reg: pub(super) -> pub(crate)
    - Adds ConstrainedReg<REG> wrapper with Deref to Reg<REG>
    """
    generic_path = pac_dir / "generic.rs"
    if not generic_path.exists():
        raise FileNotFoundError(f"generic.rs not found at {generic_path}")

    content = generic_path.read_text()
    original = content

    # --- Field visibility changes ---

    # Widen Reg.register visibility
    content = content.replace(
        "    register: vcell::VolatileCell<REG::Ux>,",
        "    pub(crate) register: vcell::VolatileCell<REG::Ux>,",
    )

    # Widen raw::R._reg visibility (pub(super) -> pub(crate))
    content = re.sub(
        r'(pub struct R<REG: RegisterSpec> \{\s*pub\(crate\) bits: REG::Ux,\s*)pub\(super\)( _reg: marker::PhantomData<REG>,)',
        r'\1pub(crate)\2',
        content,
    )
    # Widen raw::W._reg visibility (pub(super) -> pub(crate))
    content = re.sub(
        r'(pub struct W<REG: RegisterSpec> \{\s*///Writable bits\s*pub\(crate\) bits: REG::Ux,\s*)pub\(super\)( _reg: marker::PhantomData<REG>,)',
        r'\1pub(crate)\2',
        content,
    )

    # --- Add ConstrainedReg wrapper ---
    if 'pub struct ConstrainedReg' not in content:
        constrained_reg_block = (
            "\n"
            "/// A register wrapper indicating hardware write constraints exist.\n"
            "/// Forwards all operations via Deref to Reg; constraint modules add\n"
            "/// proof-requiring operation shadows as inherent methods.\n"
            "#[repr(transparent)]\n"
            "pub struct ConstrainedReg<REG: RegisterSpec> {\n"
            "    pub(crate) reg: Reg<REG>,\n"
            "}\n"
            "\n"
            "unsafe impl<REG: RegisterSpec> Send for ConstrainedReg<REG> where REG::Ux: Send {}\n"
            "\n"
            "impl<REG: RegisterSpec> core::ops::Deref for ConstrainedReg<REG> {\n"
            "    type Target = Reg<REG>;\n"
            "    #[inline(always)]\n"
            "    fn deref(&self) -> &Reg<REG> {\n"
            "        &self.reg\n"
            "    }\n"
            "}\n"
            "\n"
            "impl<REG: Readable> core::fmt::Debug for ConstrainedReg<REG>\n"
            "where\n"
            "    R<REG>: core::fmt::Debug,\n"
            "{\n"
            "    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {\n"
            "        core::fmt::Debug::fmt(&**self, f)\n"
            "    }\n"
            "}\n"
        )
        # Insert after the `unsafe impl ... Send for Reg<REG>` line
        send_line = "unsafe impl<REG: RegisterSpec> Send for Reg<REG> where REG::Ux: Send {}"
        content = content.replace(send_line, send_line + constrained_reg_block)

    if content != original:
        generic_path.write_text(content)
        print(f"  Patched generic.rs: {generic_path}")
    else:
        print(f"  generic.rs already patched (no changes needed)")


def inject_into_pac(pac_path: Path, peripheral: str, reg_name: str, module_code: str) -> None:
    """Inject a constraints module into a PAC mod.rs file.

    Inserts `pub mod constraints { ... }` inside the peripheral module,
    right after the register's sub-module closes.

    Also patches generic.rs field visibility to allow constraint module access.
    """
    # Patch generic.rs first
    pac_dir = pac_path.parent
    # generic.rs is in the src/ directory (sibling of the device dir)
    # pac_path is e.g. stm32f4/src/stm32f405/mod.rs -> generic.rs is at stm32f4/src/generic.rs
    generic_dir = pac_path.parent.parent
    patch_generic_rs(generic_dir)

    content = pac_path.read_text()
    reg_lower = reg_name.lower()

    # Find the closing of the register module inside the peripheral module.
    # We look for the pattern: `impl crate::Resettable for {REG}rs {}` followed by `}`
    # that appears inside `pub mod {peripheral} { ... pub mod {reg} { ... } }`
    # and is followed by a CR2/other register doc comment containing the peripheral name.
    marker = f"STM32F405.html#{peripheral.upper()}:{reg_name}"
    # Find the Resettable impl for this register in the right peripheral context
    search = f'impl crate::Resettable for {reg_name}rs {{}}'

    # Find all occurrences and pick the one in the right peripheral
    positions = [m.end() for m in re.finditer(re.escape(search), content)]

    # For each position, check if the surrounding context mentions our peripheral
    target_pos = None
    for pos in positions:
        # Look backwards ~2000 chars for the peripheral module declaration
        context_start = max(0, pos - 5000)
        context = content[context_start:pos]
        if f'pub mod {peripheral}' in context or f'#{peripheral.upper()}:' in context:
            # Also verify the next line closes the module (indented `}`)
            next_chunk = content[pos:pos + 50]
            if '\n    }' in next_chunk:
                # Find the closing brace
                brace_pos = pos + next_chunk.index('\n    }') + len('\n    }')
                target_pos = brace_pos
                break

    if target_pos is None:
        raise ValueError(
            f"Could not find insertion point for {peripheral}::{reg_lower} in {pac_path}"
        )

    # Build the module to inject
    indented = indent_block(module_code)
    injection = f"\n    pub mod constraints {{\n{indented}\n    }}"

    new_content = content[:target_pos] + injection + content[target_pos:]

    # Patch the register type alias to use ConstrainedReg.
    # Must find the alias within the correct peripheral module, not just the first
    # occurrence in the file (multiple peripherals may share the same register name).
    old_alias = f'pub type {reg_name} = crate::Reg<{reg_lower}::{reg_name}rs>;'
    new_alias = f'pub type {reg_name} = crate::ConstrainedReg<{reg_lower}::{reg_name}rs>;'
    # Find the peripheral module start and search for the alias after it
    periph_mod = f'pub mod {peripheral} {{'
    periph_start = new_content.find(periph_mod)
    if periph_start >= 0:
        alias_pos = new_content.find(old_alias, periph_start)
        if alias_pos >= 0:
            new_content = (
                new_content[:alias_pos]
                + new_alias
                + new_content[alias_pos + len(old_alias):]
            )

    pac_path.write_text(new_content)


def main():
    parser = argparse.ArgumentParser(
        description="Generate constraint-aware Rust code from RegisterInfo JSON"
    )
    parser.add_argument(
        "input",
        help="Path to constraints JSON file (RegisterInfo schema)",
    )
    parser.add_argument(
        "--peripheral",
        default="i2c1",
        help="Peripheral name (e.g., i2c1). Default: i2c1",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output .rs file path. Default: applications/pac_codegen/generated/<peripheral>/constraints.rs",
    )
    parser.add_argument(
        "--inject",
        default=None,
        help="Path to PAC mod.rs to inject constraints into (e.g., stm32-rs/stm32f4/src/stm32f405/mod.rs)",
    )
    args = parser.parse_args()

    # Read and validate the input JSON
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path) as f:
        data = json.load(f)

    register_info = RegisterInfo(**data)

    # Generate the Rust code
    rust_code = generate_constraint_module(register_info, args.peripheral)

    if args.inject:
        # Inject into PAC source
        pac_path = Path(args.inject)
        if not pac_path.exists():
            print(f"Error: PAC file not found: {pac_path}", file=sys.stderr)
            sys.exit(1)
        inject_into_pac(
            pac_path,
            args.peripheral,
            register_info.datasheet_register_abbreviation,
            rust_code,
        )
        print(f"Injected constraints into: {pac_path}")
    else:
        # Write standalone file
        if args.output:
            output_path = Path(args.output)
        else:
            # Default into applications/pac_codegen/generated/<peripheral>/constraints.rs,
            # kept inside this application's own directory. This file lives at
            # applications/pac_codegen/rust_codegen.py, so the app dir is one level up.
            output_path = (
                Path(__file__).resolve().parent
                / "generated"
                / args.peripheral
                / "constraints.rs"
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rust_code)
        print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
