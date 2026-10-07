# Intel 82599 — final constraints list

Committed snapshot of every access constraint found for the 75 driver-scoped registers: **29 from the canonical run r006** + **5 recovered** by the constraint-recall improvement = **34 total**. Each is schema-valid (grammar-v2) with computed enforceability. They were **not** run through the LLM constraint validator (quote-anchor + closed-book judge) — see results.md. The per-run collection files are gitignored scratch; this is the durable record.

- enforceability: {'doc_only': 27, 'dynamic_check': 1, 'state_witnessed': 1, 'action_witnessed': 5}
- kinds: {'other': 10, 'delay': 1, 'value_relation': 10, 'state_gate': 6, 'read_effect': 7}

## New bug found via the recovered RXCSUM constraint

Improving constraint recall surfaced a 9th driver bug. The recovered RXCSUM `state_gate` (“write only when RXCTRL.RXEN = 0b”) is **violated by Theseus**: `rx_init` (lib.rs:301) ends by enabling the receiver (`enable_rx_function`, RXEN=1), then `enable_rss` (lib.rs:359) writes `regs2.rxcsum` (lib.rs:912) with no re-disable — configuring RXCSUM (and the RSS block: MRQC, RSSRK, RETA) while the receiver is live. Same root cause as the FCTRL promiscuous-while-live bug (configure-after-enable). Fires whenever RSS is enabled. ixy / Redox / RedLeaf do not configure RXCSUM, so this is Theseus-only.

## Constraints

| # | Register | Kind | Enforceability | Datasheet text | Source |
|---|---|---|---|---|---|
| 1 | AUTOC | other | doc_only | Note: The 82599 Device Firmware may access AUTOC register in parallel to software driver and a synchronization between t… | r006 |
| 2 | CTRL | delay | dynamic_check | To ensure that a global device reset has fully completed and that the 82599 responds to subsequent accesses, programmers… | r006 |
| 3 | CTRL_EXT | other | doc_only | This bit should only be reset by a PCIe reset and should only be changed while Tx and Rx processes are stopped. The exce… | r006 |
| 4 | DMATXCTL | value_relation | doc_only | For proper operation, software must not change the default setting of this field (802.3ac standard defines it as 0x8100)… | r006 |
| 5 | EEC | state_gate | state_witnessed | When EE_GNT is set to 1b, the EE_SK output signal is mapped to this bit and provides the serial clock input to the EEPRO… | r006 |
| 6 | EIAC | state_gate | action_witnessed | Bits 29:20 should never set auto clear since they share the same MSI-X vector. | r006 |
| 7 | EIAM | state_gate | action_witnessed | In MSI-X mode, if any of the Auto Mask enable bits is set, the GPIE.EIAME bit must be set as well. | r006 |
| 8 | EITR | value_relation | doc_only | When CNT_WDIS is not set on a write cycle, this field must be set to 0x0. | r006 |
| 9 | FCRTH | value_relation | doc_only | This value must be at least eight bytes less than the maximum number of bytes allocated to the receive packet buffer and… | r006 |
| 10 | FCRTL | other | doc_only | The lower four bits must be programmed to 0x0 (16-byte granularity). | r006 |
| 11 | FCTRL | state_gate | action_witnessed | Note: Before receive filters are updated/modified the RXCTRL.RXEN bit should be set to 0b. After the proper filters have… | r006 |
| 12 | GORCH | read_effect | doc_only | Good Octets Received Count High — GORCH (0x0408C; RC) | r006 |
| 13 | GOTCH | read_effect | doc_only | # 8.2.3.23.46 Good Octets Transmitted Count High — GOTCH (0x04094; RC) | r006 |
| 14 | GOTCL | read_effect | doc_only | Good Octets Transmitted Count Low — GOTCL (0x04090; RC) | r006 |
| 15 | HLREG0 | value_relation | doc_only | The RDRXCTL.CRCStrip must be set the same as this bit. | r006 |
| 16 | L34TIMIR | other | doc_only | This register must be initialized by software. | r006 |
| 17 | LINKS | read_effect | doc_only | A new link partner next page was received during the backplane auto-negotiation process. Latch high, clear on read. | r006 |
| 18 | LINKS | read_effect | doc_only | KX/KX4/KR Backplane Auto Negotiation Page Received. A new link partner page was received during the auto-negotiation pro… | r006 |
| 19 | LINKS | read_effect | doc_only | 0b = Link is currently down or link was down since last time read. 1b = Link is Up and there was no link down from last … | r006 |
| 20 | RDBAL | value_relation | doc_only | The lower 7 bits are always ignored. The receive descriptor base address must point to a 128 byte-aligned block of data. | r006 |
| 21 | RDRXCTL | value_relation | doc_only | This bit must be set the same as HLREG0.RXCRCSTRP. | r006 |
| 22 | RXPBSIZE | other | doc_only | Note: In any setting the RXPBSIZE[0] must always be enabled (greater than zero). | r006 |
| 23 | SAQF | other | doc_only | This register must be initialized by software. | r006 |
| 24 | SRRCTL | value_relation | doc_only | Note: BSIZEHEADER must be bigger than zero if DESCTYPE is equal to 010b, 011b, 100b or 101b. | r006 |
| 25 | SWSM | read_effect | doc_only | This bit is set by hardware, when this register is read by the device driver (one of two PCI functions) and cleared when… | r006 |
| 26 | TDBAL | value_relation | doc_only | The lower seven bits are ignored. The Transmit Descriptor Base Address must point to a 128 byte-aligned block of data. | r006 |
| 27 | TDH | state_gate | action_witnessed | The only time that software should write to this register is after a reset (hardware reset or CTRL.RST) and before enabl… | r006 |
| 28 | TXDCTL | other | doc_only | Note: When WTHRESH is set to a non-zero value, the software driver should not set the RS bit in the Tx descriptors. When… | r006 |
| 29 | TXDCTL | other | doc_only | Note: When Head write-back is enabled (TDWBAL[n].Head_WB_En = 1b), the WTHRESH must be set to zero. | r006 |
| 30 | DAQF | other | doc_only | This register must be initialized by software. | recovered |
| 31 | RDLEN | value_relation | doc_only | It must be 128-byte aligned (7 LS bit must be set to zero). | recovered |
| 32 | RXCSUM | state_gate | action_witnessed | This register should only be initialized (written) when the receiver is not enabled (for example, only write this regist… | recovered |
| 33 | SDPQF | other | doc_only | This register must be initialized by software. | recovered |
| 34 | TDLEN | value_relation | doc_only | It must be 128-byte-aligned (7 LS bit must be set to zero). | recovered |
