# Register Access Constraints Grammar

This document describes how to encode hardware register access constraints for generating type-safe Rust PAC (Peripheral Access Crate) code using linear types.

## Purpose

The goal is to update peripheral access crates with compile-time enforceable constraints, so that drivers using the PAC crates return compilation errors when they don't follow hardware requirements from datasheets.

## Linear Type Pattern

We use **linear types** (affine types) to enforce constraints at compile time:

1. **Preconditions**: Operations consume linear type tokens, proving requirements are met
2. **Postconditions**: Operations produce linear type tokens that must be consumed, enforcing cleanup

This is a hybrid approach:
- **Runtime check** to obtain witness tokens
- **Compile-time enforcement** that checks were performed (tokens must be obtained and consumed)

## Data Model

### FieldState

Represents a field state requirement (pre or post condition):

```python
class FieldState(BaseModel):
    """Represents a field state requirement (pre or post condition)"""
    register_name: str  # Can be different register (e.g., "RTTDCS" when constraining "MTQC")
    field_name: str
    required_state: str  # "cleared", "set", "equals:<value>"
```

### RegisterAccessConstraint

Constraint on register/field access using linear types:

```python
class RegisterAccessConstraint(BaseModel):
    """
    Constraint on register/field access using linear types.

    Preconditions are enforced by consuming linear type tokens.
    Postconditions are enforced by producing linear type tokens that must be consumed elsewhere.
    """
    # What's being constrained
    target_register: str
    target_fields: list[str]  # Empty = whole register
    target_operation: str  # "write", "read", "modify"

    # Pre-conditions: linear types that must be CONSUMED
    # e.g., to write, you must consume StopClearedToken
    preconditions: list[FieldState]

    # Post-conditions: linear types that are PRODUCED and must be used elsewhere
    # e.g., writing produces ArbdisMustClearToken that must be consumed
    postconditions: list[FieldState]

    # Metadata
    severity: str  # "error", "warning"
    consequence: str
    datasheet_text: str
```

## Example 1: I2C CR1 Register (Preconditions Only)

### Datasheet Constraint

> "When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. Otherwise there is a risk of setting a second STOP, START or PEC request."

### Encoding

```python
RegisterAccessConstraint(
    target_register="I2C_CR1",
    target_fields=[],
    target_operation="write",

    # Must consume these tokens (proving the fields are cleared)
    preconditions=[
        FieldState(register_name="I2C_CR1", field_name="STOP", required_state="cleared"),
        FieldState(register_name="I2C_CR1", field_name="START", required_state="cleared"),
        FieldState(register_name="I2C_CR1", field_name="PEC", required_state="cleared"),
    ],

    # No postconditions (doesn't produce tokens)
    postconditions=[],

    severity="error",
    consequence="Risk of setting second STOP, START, or PEC request",
    datasheet_text="When the STOP, START or PEC bit is set, the software must not perform any write access to I2C_CR1 before this bit is cleared by hardware. Otherwise there is a risk of setting a second STOP, START or PEC request."
)
```

### Generated Rust Code

```rust
// Witness tokens (zero-sized types)
pub struct StopClearedToken(());
pub struct StartClearedToken(());
pub struct PecClearedToken(());

impl CR1 {
    /// Check if STOP bit is cleared. Returns a witness token if true.
    pub fn verify_stop_cleared(&self) -> Result<StopClearedToken, I2cError> {
        if self.read().stop().bit_is_clear() {
            Ok(StopClearedToken(()))
        } else {
            Err(I2cError::StopBitNotCleared)
        }
    }

    pub fn verify_start_cleared(&self) -> Result<StartClearedToken, I2cError> {
        if self.read().start().bit_is_clear() {
            Ok(StartClearedToken(()))
        } else {
            Err(I2cError::StartBitNotCleared)
        }
    }

    pub fn verify_pec_cleared(&self) -> Result<PecClearedToken, I2cError> {
        if self.read().pec().bit_is_clear() {
            Ok(PecClearedToken(()))
        } else {
            Err(I2cError::PecBitNotCleared)
        }
    }

    /// Write to CR1. Requires witness tokens proving preconditions are met.
    /// Tokens are consumed (moved) to prevent reuse.
    pub fn write_safe(
        &mut self,
        f: impl FnOnce(&mut W) -> &mut W,
        _stop: StopClearedToken,
        _start: StartClearedToken,
        _pec: PecClearedToken
    ) {
        // Tokens consumed here, can only be used once
        self.write(f)
    }
}
```

### Usage

```rust
// Runtime checks produce tokens
let stop = cr1.verify_stop_cleared()?;
let start = cr1.verify_start_cleared()?;
let pec = cr1.verify_pec_cleared()?;

// Compile-time: must provide tokens to write
cr1.write_safe(|w| w.bits(value), stop, start, pec);

// Tokens are consumed and cannot be reused
```

## Example 2: MTQC Register (Pre AND Post Conditions)

### Datasheet Constraint

> "Programming MTQC must be done only during the init phase while software must also set RTTDCS.ARBDIS before configuring MTQC and then clear RTTDCS.ARBDIS afterwards"

### Encoding

```python
RegisterAccessConstraint(
    target_register="MTQC",
    target_fields=[],
    target_operation="write",

    # Must consume token proving ARBDIS is set
    preconditions=[
        FieldState(register_name="RTTDCS", field_name="ARBDIS", required_state="set")
    ],

    # Produces token that MUST be consumed (by clearing ARBDIS)
    postconditions=[
        FieldState(register_name="RTTDCS", field_name="ARBDIS", required_state="cleared")
    ],

    severity="error",
    consequence="Undefined behavior if ARBDIS not cleared after MTQC write",
    datasheet_text="Programming MTQC must be done only during the init phase while software must also set RTTDCS.ARBDIS before configuring MTQC and then clear RTTDCS.ARBDIS afterwards"
)
```

Note: The "init phase only" constraint is handled at the peripheral level API design, not by this register constraint.

### Generated Rust Code

```rust
/// Token proving ARBDIS is set (produced by set operation)
pub struct ArbdisSetToken(());

/// Token that MUST be consumed by clearing ARBDIS
#[must_use = "ARBDIS must be cleared after MTQC write"]
pub struct ArbdisMustClearToken(());

impl RTTDCS {
    /// Set ARBDIS, returns token
    pub fn set_arbdis(&mut self) -> ArbdisSetToken {
        self.modify(|_, w| w.arbdis().set_bit());
        ArbdisSetToken(())
    }

    /// Clear ARBDIS, consumes the must-clear token
    pub fn clear_arbdis(&mut self, _token: ArbdisMustClearToken) {
        self.modify(|_, w| w.arbdis().clear_bit());
        // token consumed
    }
}

impl MTQC {
    /// Write MTQC, consumes set token, produces must-clear token
    pub fn write(
        &mut self,
        value: u32,
        _arbdis_set: ArbdisSetToken  // Consumed (precondition)
    ) -> ArbdisMustClearToken {      // Produced (postcondition)
        self.write(|w| unsafe { w.bits(value) });
        ArbdisMustClearToken(())     // MUST be used
    }
}
```

### Usage

```rust
// Set ARBDIS and get precondition token
let set_token = rttdcs.set_arbdis();

// Write MTQC (consumes precondition, produces postcondition)
let must_clear = mtqc.write(0x1234, set_token);

// Must consume postcondition token
rttdcs.clear_arbdis(must_clear);

// Compiler enforces:
// 1. Can't write MTQC without setting ARBDIS first (need the token)
// 2. Can't forget to clear ARBDIS (must_clear token must be used)
```

## Key Patterns

### Preconditions Only
- Hardware clears bits automatically
- Driver must verify state before operation
- **Pattern**: Verify methods produce tokens, operation consumes them
- **Example**: I2C_CR1 (hardware clears STOP/START/PEC)

### Preconditions + Postconditions
- Software must set state before, clear state after
- **Pattern**: Set operation produces token (precondition), write operation consumes it and produces new token (postcondition), clear operation consumes postcondition
- **Example**: MTQC (set ARBDIS before, clear ARBDIS after)

### Multiple Register Coordination
- Constraints can span multiple registers
- Use `register_name` in `FieldState` to reference other registers
- **Example**: MTQC write depends on RTTDCS.ARBDIS state

## Benefits

1. **Compile-time safety**: Impossible to violate constraints without explicitly bypassing safety
2. **Self-documenting**: API signatures encode requirements
3. **Zero runtime cost**: Tokens are zero-sized types, optimized away
4. **Explicit errors**: Clear compilation errors guide developers
5. **Linear types**: Tokens can only be used once, preventing state tracking bugs

## Integration with RegisterInfo

```python
class RegisterInfo(BaseModel):
    datasheet_register_abbreviation: str
    address_offset: str
    reset_value: str
    size: int
    subfields: list[BitField]
    access_constraints: list[RegisterAccessConstraint]  # Linear type constraints
```
