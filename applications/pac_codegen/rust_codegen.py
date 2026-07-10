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
    postconditions: list[FieldState]
    datasheet_texts: list[str]


def normalize_constraints(register_info: RegisterInfo) -> list[NormalizedConstraint]:
    """Group constraints by operation and deduplicate predicates deterministically."""
    plans: dict[str, NormalizedConstraint] = {}
    seen_preconditions: dict[str, set[tuple[str, str, str, str, str | None]]] = {}
    seen_postconditions: dict[str, set[tuple[str, str, str, str, str | None]]] = {}
    seen_fields: dict[str, set[str]] = {}

    for constraint in register_info.access_constraints:
        operation = constraint.target_operation
        if operation not in plans:
            plans[operation] = NormalizedConstraint(
                target_register=constraint.target_register,
                target_fields=[],
                target_operation=operation,
                preconditions=[],
                postconditions=[],
                datasheet_texts=[],
            )
            seen_preconditions[operation] = set()
            seen_postconditions[operation] = set()
            seen_fields[operation] = set()

        plan = plans[operation]
        for field in constraint.target_fields:
            if field not in seen_fields[operation]:
                plan.target_fields.append(field)
                seen_fields[operation].add(field)

        for precondition in constraint.preconditions:
            key = (
                precondition.register_name,
                precondition.field_name,
                precondition.required_state,
                precondition.evidence_kind,
                precondition.action_operation,
            )
            if key not in seen_preconditions[operation]:
                plan.preconditions.append(precondition)
                seen_preconditions[operation].add(key)

        for postcondition in constraint.postconditions:
            key = (
                postcondition.register_name,
                postcondition.field_name,
                postcondition.required_state,
                postcondition.evidence_kind,
                postcondition.action_operation,
            )
            if key not in seen_postconditions[operation]:
                plan.postconditions.append(postcondition)
                seen_postconditions[operation].add(key)

        if constraint.datasheet_text not in plan.datasheet_texts:
            plan.datasheet_texts.append(constraint.datasheet_text)

    return list(plans.values())


def field_to_rust_name(field_name: str) -> str:
    """Map a field name to its svd2rust accessor (lowercase)."""
    return field_name.lower()


def operation_to_proof_name(register_name: str, operation: str) -> str:
    """Generate the private-constructor proof type for an operation."""
    return f"{register_name.capitalize()}{operation.capitalize()}Ready"


def _state_name(state: str) -> str:
    if state == "set":
        return "Set"
    if state == "cleared":
        return "Cleared"
    if state.startswith("equals:"):
        value = re.sub(r"[^A-Za-z0-9]", "", state.split(":", 1)[1])
        return f"Eq{value}"
    raise ValueError(f"Unknown state: {state}")


def action_token_name(field_state: FieldState) -> str:
    return f"{field_state.field_name.capitalize()}{_state_name(field_state.required_state)}"


def obligation_token_name(field_state: FieldState) -> str:
    if field_state.required_state == "cleared":
        state = "Clear"
    elif field_state.required_state == "set":
        state = "Set"
    elif field_state.required_state.startswith("equals:"):
        value = re.sub(
            r"[^A-Za-z0-9]",
            "",
            field_state.required_state.split(":", 1)[1],
        )
        state = f"SetTo{value}"
    else:
        raise ValueError(f"Unknown state: {field_state.required_state}")
    return f"{field_state.field_name.capitalize()}Must{state}"


def _observed_preconditions(
    constraint: NormalizedConstraint,
) -> list[FieldState]:
    return [
        precondition
        for precondition in constraint.preconditions
        if precondition.evidence_kind == "observed_state"
    ]


def _action_preconditions(
    constraint: NormalizedConstraint,
) -> list[FieldState]:
    return [
        precondition
        for precondition in constraint.preconditions
        if precondition.evidence_kind == "software_action"
    ]


def _action_postconditions(
    constraint: NormalizedConstraint,
) -> list[FieldState]:
    return [
        postcondition
        for postcondition in constraint.postconditions
        if postcondition.evidence_kind == "software_action"
    ]


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


def state_to_check(
    field_name: str,
    state: str,
    reader_name: str = "r",
) -> str:
    """Generate a Rust check expression for a field state.

    Returns a string like `r.stop().bit_is_clear()`.
    """
    accessor = field_to_rust_name(field_name)
    if state == "cleared":
        return f"{reader_name}.{accessor}().bit_is_clear()"
    elif state == "set":
        return f"{reader_name}.{accessor}().bit_is_set()"
    elif state.startswith("equals:"):
        val = state.split(":", 1)[1]
        return f"{reader_name}.{accessor}().bits() == {val}"
    else:
        raise ValueError(f"Unknown state: {state}")


def _register_matches_target(
    register_name: str,
    register_abbreviation: str,
    target_register: str,
) -> bool:
    candidate = register_name.upper()
    targets = {register_abbreviation.upper(), target_register.upper()}
    return candidate in targets or any(
        candidate.endswith(f"_{target}") for target in targets
    )


def _pac_register_name(register_name: str, peripheral: str) -> str:
    prefix = f"{peripheral.upper()}_"
    if register_name.upper().startswith(prefix):
        return register_name[len(prefix):]
    return register_name


def _is_same_register_constraint(
    constraint: NormalizedConstraint,
    register_name: str,
) -> bool:
    preconditions = _observed_preconditions(constraint)
    if not preconditions:
        return True
    return all(
        _register_matches_target(
            precondition.register_name,
            register_name,
            constraint.target_register,
        )
        for precondition in preconditions
    )


def _source_register_name(
    precondition: FieldState,
    constraint: NormalizedConstraint,
    register_name: str,
) -> str:
    if _register_matches_target(
        precondition.register_name,
        register_name,
        constraint.target_register,
    ):
        return register_name
    return precondition.register_name


def _error_variant_for_precondition(
    precondition: FieldState,
    constraint: NormalizedConstraint,
    register_name: str,
) -> str:
    prefix = ""
    if not _register_matches_target(
        precondition.register_name,
        register_name,
        constraint.target_register,
    ):
        prefix = precondition.register_name.capitalize()
    return prefix + field_to_error_variant(
        precondition.field_name,
        precondition.required_state,
    )


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
    error_name = f"{reg_name.capitalize()}ConstraintError"
    lines.append(
        f"    /// Read {reg_name} once and verify every {operation} precondition."
    )
    lines.append("    #[inline(always)]")
    lines.append(
        f"    pub fn verify_{operation}_ready(&self) "
        f"-> Result<{proof_name}, {error_name}> {{"
    )
    lines.append("        let r = self.reg.read();")
    for precondition in _observed_preconditions(constraint):
        error_variant = _error_variant_for_precondition(
            precondition,
            constraint,
            reg_name,
        )
        check_expr = state_to_check(
            precondition.field_name,
            precondition.required_state,
        )
        lines.append(f"        if !({check_expr}) {{")
        lines.append(
            f"            return Err({error_name}::{error_variant});"
        )
        lines.append("        }")
    lines.append(f"        Ok({proof_name}(()))")
    lines.append("    }")
    lines.append("")


def _append_cross_register_verifier(
    lines: list[str],
    constraint: NormalizedConstraint,
    reg_name: str,
) -> None:
    operation = constraint.target_operation
    proof_name = operation_to_proof_name(reg_name, operation)
    error_name = f"{reg_name.capitalize()}ConstraintError"
    sources: list[str] = []
    for precondition in _observed_preconditions(constraint):
        source = _source_register_name(
            precondition,
            constraint,
            reg_name,
        )
        if source not in sources:
            sources.append(source)

    parameters = ", ".join(
        f"{field_to_rust_name(source)}: "
        f"&crate::Reg<super::{field_to_rust_name(source)}::"
        f"{source.upper()}rs>"
        for source in sources
    )
    function_name = (
        f"verify_{field_to_rust_name(reg_name)}_{operation}_ready"
    )
    _constraint_doc_lines(lines, constraint)
    lines.append("#[inline(always)]")
    lines.append(
        f"pub fn {function_name}({parameters}) "
        f"-> Result<{proof_name}, {error_name}> {{"
    )
    for source in sources:
        variable = field_to_rust_name(source)
        lines.append(f"    let {variable}_state = {variable}.read();")
    for precondition in _observed_preconditions(constraint):
        source = _source_register_name(
            precondition,
            constraint,
            reg_name,
        )
        reader_name = f"{field_to_rust_name(source)}_state"
        check_expr = state_to_check(
            precondition.field_name,
            precondition.required_state,
            reader_name,
        )
        error_variant = _error_variant_for_precondition(
            precondition,
            constraint,
            reg_name,
        )
        lines.append(f"    if !({check_expr}) {{")
        lines.append(
            f"        return Err({error_name}::{error_variant});"
        )
        lines.append("    }")
    lines.append(f"    Ok({proof_name}(()))")
    lines.append("}")
    lines.append("")


def _authorization_parameters(
    constraint: NormalizedConstraint,
    reg_name: str,
    *,
    consumed: bool,
) -> list[tuple[str, str]]:
    parameters: list[tuple[str, str]] = []
    if _observed_preconditions(constraint):
        name = "_proof" if consumed else "proof"
        parameters.append(
            (
                name,
                operation_to_proof_name(
                    reg_name,
                    constraint.target_operation,
                ),
            )
        )
    for precondition in _action_preconditions(constraint):
        base = (
            f"{field_to_rust_name(precondition.field_name)}_"
            f"{_state_name(precondition.required_state).lower()}"
        )
        name = f"_{base}" if consumed else base
        item = (name, action_token_name(precondition))
        if item not in parameters:
            parameters.append(item)
    return parameters


def _parameter_suffix(parameters: list[tuple[str, str]]) -> str:
    if not parameters:
        return ""
    return ", " + ", ".join(
        f"{name}: {type_name}" for name, type_name in parameters
    )


def _parameter_names(parameters: list[tuple[str, str]]) -> str:
    return ", ".join(name.lstrip("_") for name, _ in parameters)


def _action_postcondition(
    constraint: NormalizedConstraint,
) -> FieldState | None:
    postconditions = _action_postconditions(constraint)
    if len(postconditions) > 1:
        raise ValueError(
            "Action-derived codegen currently supports one postcondition "
            f"per {constraint.target_register} "
            f"{constraint.target_operation} operation"
        )
    return postconditions[0] if postconditions else None


def _result_type(result_type: str, constraint: NormalizedConstraint) -> str:
    postcondition = _action_postcondition(constraint)
    if postcondition is None:
        return result_type
    return f"{obligation_token_name(postcondition)}<{result_type}>"


def _result_expression(
    expression: str,
    constraint: NormalizedConstraint,
) -> str:
    postcondition = _action_postcondition(constraint)
    if postcondition is None:
        return expression
    return f"{obligation_token_name(postcondition)}({expression})"


def _action_method_name(field_state: FieldState) -> str:
    field = field_to_rust_name(field_state.field_name)
    if field_state.required_state == "set":
        return f"set_{field}"
    if field_state.required_state == "cleared":
        return f"clear_{field}"
    if field_state.required_state.startswith("equals:"):
        value = re.sub(
            r"[^A-Za-z0-9]",
            "_",
            field_state.required_state.split(":", 1)[1],
        ).strip("_")
        return f"set_{field}_to_{value.lower()}"
    raise ValueError(f"Unknown state: {field_state.required_state}")


def _action_write_expression(field_state: FieldState) -> str:
    field = field_to_rust_name(field_state.field_name)
    if field_state.required_state == "set":
        writer = f"w.{field}().set_bit()"
    elif field_state.required_state == "cleared":
        writer = f"w.{field}().clear_bit()"
    elif field_state.required_state.startswith("equals:"):
        value = field_state.required_state.split(":", 1)[1]
        writer = f"unsafe {{ w.{field}().bits({value}) }}"
    else:
        raise ValueError(f"Unknown state: {field_state.required_state}")

    if field_state.action_operation == "modify":
        return f"self.reg.modify(|_, w| {writer})"
    if field_state.action_operation == "write":
        return f"self.reg.write(|w| {writer})"
    raise ValueError(
        "software_action field states require action_operation "
        f"for {field_state.register_name}.{field_state.field_name}"
    )


def _append_action_support(
    lines: list[str],
    constraints: list[NormalizedConstraint],
    peripheral: str,
) -> None:
    setup_states: list[FieldState] = []
    cleanup_states: list[FieldState] = []
    for constraint in constraints:
        for precondition in _action_preconditions(constraint):
            if precondition not in setup_states:
                setup_states.append(precondition)
        for postcondition in _action_postconditions(constraint):
            if postcondition not in cleanup_states:
                cleanup_states.append(postcondition)

    if not setup_states and not cleanup_states:
        return

    lines.extend(
        [
            "// === Action-Derived Witnesses ===",
            "",
        ]
    )
    emitted_types: dict[str, tuple[str, str, str]] = {}
    for state in setup_states:
        type_name = action_token_name(state)
        identity = (
            state.register_name,
            state.field_name,
            state.required_state,
        )
        if type_name in emitted_types and emitted_types[type_name] != identity:
            raise ValueError(f"Conflicting action token name: {type_name}")
        if type_name not in emitted_types:
            lines.append(
                f"/// Proof that software established "
                f"{state.register_name}.{state.field_name} as "
                f"{state.required_state}."
            )
            lines.append(f"pub struct {type_name}(());")
            lines.append("")
            emitted_types[type_name] = identity
    for state in cleanup_states:
        type_name = obligation_token_name(state)
        identity = (
            state.register_name,
            state.field_name,
            state.required_state,
        )
        if type_name in emitted_types and emitted_types[type_name] != identity:
            raise ValueError(f"Conflicting obligation token name: {type_name}")
        if type_name not in emitted_types:
            lines.append(
                f"#[must_use = \"{state.register_name}.{state.field_name} "
                f"must be {state.required_state}\"]"
            )
            lines.append(
                f"pub struct {type_name}<T>(T);"
            )
            lines.append("")
            emitted_types[type_name] = identity

    by_source: dict[str, tuple[list[FieldState], list[FieldState]]] = {}
    for state in setup_states:
        source = _pac_register_name(state.register_name, peripheral)
        by_source.setdefault(source, ([], []))[0].append(state)
    for state in cleanup_states:
        source = _pac_register_name(state.register_name, peripheral)
        by_source.setdefault(source, ([], []))[1].append(state)

    for source, (setups, cleanups) in by_source.items():
        source_lower = field_to_rust_name(source)
        source_upper = source.upper()
        setup_names = {_action_method_name(state) for state in setups}
        cleanup_names = {_action_method_name(state) for state in cleanups}
        collisions = setup_names & cleanup_names
        if collisions:
            raise ValueError(
                f"Setup and cleanup methods collide for {source}: "
                f"{sorted(collisions)}"
            )
        lines.append(
            f"impl crate::ConstrainedReg<"
            f"super::{source_lower}::{source_upper}rs> {{"
        )
        for state in setups:
            method = _action_method_name(state)
            token = action_token_name(state)
            lines.extend(
                [
                    "    #[inline(always)]",
                    f"    pub fn {method}(&self) -> {token} {{",
                    f"        {_action_write_expression(state)};",
                    f"        {token}(())",
                    "    }",
                    "",
                ]
            )
        for state in cleanups:
            method = _action_method_name(state)
            obligation = obligation_token_name(state)
            lines.extend(
                [
                    "    #[inline(always)]",
                    f"    pub fn {method}<T>(&self, obligation: {obligation}<T>) -> T {{",
                    f"        {_action_write_expression(state)};",
                    "        obligation.0",
                    "    }",
                    "",
                ]
            )
        lines.extend(["}", ""])


def _append_write_methods(
    lines: list[str],
    constraint: NormalizedConstraint,
    reg_name: str,
    reg_spec: str,
) -> None:
    ux = f"<{reg_spec} as crate::RegisterSpec>::Ux"
    consumed = _authorization_parameters(
        constraint,
        reg_name,
        consumed=True,
    )
    public = _authorization_parameters(
        constraint,
        reg_name,
        consumed=False,
    )
    consumed_suffix = _parameter_suffix(consumed)
    public_suffix = _parameter_suffix(public)
    call_args = _parameter_names(public)
    call_suffix = f", {call_args}" if call_args else ""
    ux_result = _result_type(ux, constraint)
    generic_result = _result_type("T", constraint)
    unit_result = _result_type("()", constraint)
    reset_return = (
        "" if unit_result == "()" else f" -> {unit_result}"
    )
    reset_expression = (
        "self.reg.reset()"
        if unit_result == "()"
        else _result_expression("{ self.reg.reset(); () }", constraint)
    )
    _constraint_doc_lines(lines, constraint, "    ")
    lines.extend(
        [
            "    #[inline(always)]",
            f"    pub fn write_constrained<F>(&self, f: F{consumed_suffix}) -> {ux_result}",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> &mut crate::W<{reg_spec}>,",
            "    {",
            f"        {_result_expression('self.reg.write(f)', constraint)}",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn write<F>(&self, f: F{public_suffix}) -> {ux_result}",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> &mut crate::W<{reg_spec}>,",
            "    {",
            f"        self.write_constrained(f{call_suffix})",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn reset_constrained(&self{consumed_suffix}){reset_return} {{",
            f"        {reset_expression}",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn reset(&self{public_suffix}){reset_return} {{",
            f"        self.reset_constrained({call_args})" if call_args else "        self.reset_constrained()",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn write_with_zero_constrained<F>(&self, f: F{consumed_suffix}) -> {ux_result}",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> &mut crate::W<{reg_spec}>,",
            "    {",
            f"        {_result_expression('self.reg.write_with_zero(f)', constraint)}",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn write_with_zero<F>(&self, f: F{public_suffix}) -> {ux_result}",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> &mut crate::W<{reg_spec}>,",
            "    {",
            f"        self.write_with_zero_constrained(f{call_suffix})",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn from_write_constrained<F, T>(&self, f: F{consumed_suffix}) -> {generic_result}",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> T,",
            "    {",
            f"        {_result_expression('self.reg.from_write(f)', constraint)}",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn from_write<F, T>(&self, f: F{public_suffix}) -> {generic_result}",
            "    where",
            f"        F: FnOnce(&mut crate::W<{reg_spec}>) -> T,",
            "    {",
            f"        self.from_write_constrained(f{call_suffix})",
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
    ux = f"<{reg_spec} as crate::RegisterSpec>::Ux"
    consumed = _authorization_parameters(
        constraint,
        reg_name,
        consumed=True,
    )
    public = _authorization_parameters(
        constraint,
        reg_name,
        consumed=False,
    )
    consumed_suffix = _parameter_suffix(consumed)
    public_suffix = _parameter_suffix(public)
    call_args = _parameter_names(public)
    call_suffix = f", {call_args}" if call_args else ""
    ux_result = _result_type(ux, constraint)
    generic_result = _result_type("T", constraint)
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
            f"    pub fn modify_constrained<F>(&self, f: F{consumed_suffix}) -> {ux_result}",
            "    where",
            f"        {callback}",
            "    {",
            f"        {_result_expression('self.reg.modify(f)', constraint)}",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn modify<F>(&self, f: F{public_suffix}) -> {ux_result}",
            "    where",
            f"        {callback}",
            "    {",
            f"        self.modify_constrained(f{call_suffix})",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn from_modify_constrained<F, T>(&self, f: F{consumed_suffix}) -> {generic_result}",
            "    where",
            f"        {callback_value}",
            "    {",
            f"        {_result_expression('self.reg.from_modify(f)', constraint)}",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn from_modify<F, T>(&self, f: F{public_suffix}) -> {generic_result}",
            "    where",
            f"        {callback_value}",
            "    {",
            f"        self.from_modify_constrained(f{call_suffix})",
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
    reader = f"crate::R<{reg_spec}>"
    consumed = _authorization_parameters(
        constraint,
        reg_name,
        consumed=True,
    )
    public = _authorization_parameters(
        constraint,
        reg_name,
        consumed=False,
    )
    consumed_suffix = _parameter_suffix(consumed)
    public_suffix = _parameter_suffix(public)
    call_args = _parameter_names(public)
    reader_result = _result_type(reader, constraint)
    _constraint_doc_lines(lines, constraint, "    ")
    lines.extend(
        [
            "    #[inline(always)]",
            f"    pub fn read_constrained(&self{consumed_suffix}) -> {reader_result} {{",
            f"        {_result_expression('self.reg.read()', constraint)}",
            "    }",
            "",
            "    #[inline(always)]",
            f"    pub fn read(&self{public_suffix}) -> {reader_result} {{",
            f"        self.read_constrained({call_args})" if call_args else "        self.read_constrained()",
            "    }",
            "",
        ]
    )


def generate_constraint_module(
    register_info: RegisterInfo,
    peripheral: str,
    include_header: bool = True,
    include_action_support: bool = True,
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
        constraint
        for constraint in constraints
        if constraint.preconditions or constraint.postconditions
    ]
    observed_constraints = [
        constraint
        for constraint in constraints
        if _observed_preconditions(constraint)
    ]

    if include_header:
        lines = [
            f"//! Compile-time access constraints for {peripheral.upper()} {reg_name}.",
            "//!",
            "//! Generated from datasheet constraints. Do not edit manually.",
            "//!",
            "//! Each constrained operation requires its own affine composite proof.",
            "",
        ]
    else:
        lines = [f"// === {reg_name} access constraints ===", ""]
    if not constraints:
        lines.append("// No access constraints defined for this register.")
        return "\n".join(lines)

    if include_action_support:
        _append_action_support(lines, constraints, peripheral)

    if observed_constraints:
        lines.extend(
            [
                "// === Composite Proofs ===",
                "// Private constructors ensure proofs only come from fresh verification.",
                "",
            ]
        )
        for constraint in observed_constraints:
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
                f"pub enum {reg_name.capitalize()}ConstraintError {{",
            ]
        )
        seen_errors: set[str] = set()
        for constraint in observed_constraints:
            for precondition in _observed_preconditions(constraint):
                variant = _error_variant_for_precondition(
                    precondition,
                    constraint,
                    reg_name,
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

    for constraint in observed_constraints:
        if not _is_same_register_constraint(constraint, reg_name):
            _append_cross_register_verifier(
                lines,
                constraint,
                reg_name,
            )

    reg_spec = f"super::{reg_lower}::{reg_name}rs"
    lines.append(f"impl crate::ConstrainedReg<{reg_spec}> {{")
    for constraint in observed_constraints:
        if _is_same_register_constraint(constraint, reg_name):
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


def generate_peripheral_constraint_module(
    register_infos: list[RegisterInfo],
    peripheral: str,
) -> str:
    """Generate one flat constraints module for a complete peripheral."""
    lines = [
        f"//! Compile-time access constraints for {peripheral.upper()} registers.",
        "//!",
        "//! Generated from trusted register constraints. Do not edit manually.",
        "",
    ]
    all_constraints = [
        constraint
        for register_info in register_infos
        for constraint in normalize_constraints(register_info)
    ]
    constrained_operations = {
        register_info.datasheet_register_abbreviation.upper(): {
            constraint.target_operation
            for constraint in normalize_constraints(register_info)
        }
        for register_info in register_infos
    }
    for constraint in all_constraints:
        for state in (
            _action_preconditions(constraint)
            + _action_postconditions(constraint)
        ):
            source_operations = constrained_operations.get(
                _pac_register_name(
                    state.register_name,
                    peripheral,
                ).upper(),
                set(),
            )
            if state.action_operation in source_operations:
                raise ValueError(
                    f"Action {state.register_name}.{state.field_name} uses "
                    f"constrained {state.action_operation}; nested action "
                    "proof composition is not yet supported"
                )
    _append_action_support(lines, all_constraints, peripheral)

    for register_info in register_infos:
        lines.append(
            generate_constraint_module(
                register_info,
                peripheral,
                include_header=False,
                include_action_support=False,
            ).rstrip()
        )
        lines.append("")
    return "\n".join(lines).rstrip()


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


def inject_into_pac_batch(
    pac_path: Path,
    peripheral: str,
    register_infos: list[RegisterInfo],
    module_code: str,
) -> None:
    """Inject one peripheral module and patch every constrained target alias."""
    if not register_infos:
        raise ValueError("At least one constrained register is required")

    first_register = register_infos[0].datasheet_register_abbreviation
    wrapped_registers = [
        register_info.datasheet_register_abbreviation
        for register_info in register_infos
    ]
    for register_info in register_infos:
        for constraint in normalize_constraints(register_info):
            for state in (
                _action_preconditions(constraint)
                + _action_postconditions(constraint)
            ):
                source_register = _pac_register_name(
                    state.register_name,
                    peripheral,
                )
                if source_register not in wrapped_registers:
                    wrapped_registers.append(source_register)
    inject_into_pac(
        pac_path,
        peripheral,
        first_register,
        module_code,
    )
    content = pac_path.read_text()
    peripheral_start = content.find(f"pub mod {peripheral} {{")
    if peripheral_start < 0:
        raise ValueError(f"Peripheral module {peripheral} not found")

    for register_name in wrapped_registers[1:]:
        reg_lower = register_name.lower()
        old_alias = (
            f"pub type {register_name} = "
            f"crate::Reg<{reg_lower}::{register_name}rs>;"
        )
        new_alias = (
            f"pub type {register_name} = "
            f"crate::ConstrainedReg<{reg_lower}::{register_name}rs>;"
        )
        alias_position = content.find(old_alias, peripheral_start)
        if alias_position < 0:
            raise ValueError(
                f"Register alias {peripheral}::{register_name} not found"
            )
        content = (
            content[:alias_position]
            + new_alias
            + content[alias_position + len(old_alias):]
        )

    pac_path.write_text(content)


def main():
    parser = argparse.ArgumentParser(
        description="Generate constraint-aware Rust code from RegisterInfo JSON"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to constraints JSON file (RegisterInfo schema)",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Grouped peripheral manifest produced by collect_constraints.py",
    )
    parser.add_argument(
        "--peripheral",
        default=None,
        help="Peripheral name; required for multi-peripheral manifests",
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

    if bool(args.input) == bool(args.manifest):
        parser.error("provide exactly one input JSON or --manifest")

    register_infos: list[RegisterInfo]
    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.exists():
            parser.error(f"manifest not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text())
        peripherals = manifest.get("peripherals", [])
        if args.peripheral:
            selected = [
                item
                for item in peripherals
                if item["name"].lower() == args.peripheral.lower()
            ]
        elif len(peripherals) == 1:
            selected = peripherals
        else:
            parser.error(
                "--peripheral is required for a multi-peripheral manifest"
            )
        if not selected:
            parser.error(f"peripheral {args.peripheral!r} not found")
        peripheral = selected[0]["name"]
        register_infos = [
            RegisterInfo(**entry["register_info"])
            for entry in selected[0]["registers"]
        ]
        rust_code = generate_peripheral_constraint_module(
            register_infos,
            peripheral,
        )
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            parser.error(f"input not found: {input_path}")
        peripheral = args.peripheral or "i2c1"
        register_infos = [
            RegisterInfo(**json.loads(input_path.read_text()))
        ]
        rust_code = generate_constraint_module(
            register_infos[0],
            peripheral,
        )

    if args.inject:
        pac_path = Path(args.inject)
        if not pac_path.exists():
            print(f"Error: PAC file not found: {pac_path}", file=sys.stderr)
            sys.exit(1)
        inject_into_pac_batch(
            pac_path,
            peripheral,
            register_infos,
            rust_code,
        )
        print(f"Injected constraints into: {pac_path}")
    else:
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = (
                Path(__file__).resolve().parent
                / "generated"
                / peripheral
                / "constraints.rs"
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rust_code)
        print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
