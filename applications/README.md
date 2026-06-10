# applications/ — downstream consumers of validated invariants

This directory is organized **by application**: each subfolder is a
self-contained consumer of the register invariants that the pipeline
(extraction → validation) produces. The two arms of LIDAR map to the two ways an
extracted invariant can be acted on, depending on whether an SVD can express it:

```
applications/
├── pac_codegen/     Enforcement arm — register DEPENDENCY / ordering invariants
│                    (not expressible in an SVD) compiled into Rust PAC code with
│                    linear types / typestate, so illegal access sequences fail to
│                    compile. Validated by the Rust compiler + conformance tests.
│
└── bug_finding/     (planned) Reporting arm — register LAYOUT invariants
                     (address offset, reset value, size, bit offset/width, access)
                     diffed against the vendor SVD/PAC; discrepancies filed as
                     upstream bug reports. Validated by upstream merges.
```

Each application is built and run independently and keeps its own inputs,
generated outputs, tooling, and (where relevant) vendored dependencies inside its
own folder. See each subfolder's `README.md` for details.

The `bug_finding/` arm is not yet built (its differential oracle is later work);
its register-layout diffing currently lives in the core pipeline and will be
factored out into its own application here when that arm is implemented.
