#!/usr/bin/env python3
"""Retrofit demonstration 2: port Redox's ixgbed onto the generated 82599 HAL.

Same shape as port_ixy.py: installs the gated --plain HAL, replaces the four
offset-based MMIO helpers (read_reg/write_reg/write_flag/clear_flag + the two
wait loops) with seven typed region accessors over the mapped BAR0, rewrites
every register site, and threads the witnesses (RXEN window incl. both
promiscuous toggles, TDH, CRC-strip coupling, EIAC clamp, DMATXCTL hold —
Redox has ixy's same absolute DMATXCTL=TE write that zeroes VT).

Semantic note (recorded): Redox's write_reg did a volatile read-back after
every write (posted-write flush); the typed writes do not — matching the
Theseus reference driver's semantics.

Every replacement asserted; not idempotent — re-clone to re-run.
Usage: python3 port_redox.py [run_tag]   (default r006)
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = sys.argv[1] if len(sys.argv) > 1 else "r006"
DRV = os.path.join(HERE, "clones", "base", "drivers", "net", "ixgbed")
HAL = os.path.join(HERE, "..", "pipeline", "hal_out", f"{RUN}-gated-plain", "regs.rs")

n_subs = 0


def sub(src, pattern, repl, count=1, flags=0):
    global n_subs
    new, n = re.subn(pattern, repl, src, flags=flags)
    assert n == count, f"matched {n} (wanted {count}): {pattern[:80]}"
    n_subs += n
    return new


shutil.copy(HAL, os.path.join(DRV, "src", "regs.rs"))
p = os.path.join(DRV, "Cargo.toml")
s = open(p).read()
if "volatile" not in s:
    s = sub(s, r"\[dependencies\]", "[dependencies]\nvolatile = \"0.2\"")
open(p, "w").write(s)
p = os.path.join(DRV, "src", "main.rs")
s = open(p).read()
if "mod regs;" not in s:
    s = sub(s, r"(mod ixgbe;)", r"\1\nmod regs;")
open(p, "w").write(s)

p = os.path.join(DRV, "src", "device.rs")
s = open(p).read()
s = sub(s, r"(use crate::ixgbe::\*;)", r"\1\nuse crate::regs::*;")

# replace the helper block (read_reg .. wait_write_reg) with typed accessors
lines = s.split("\n")
i0 = next(i for i, l in enumerate(lines) if "fn read_reg(&self, register: u32)" in l)
while lines[i0 - 1].strip().startswith("///"):
    i0 -= 1
i1 = next(i for i, l in enumerate(lines) if "fn wait_write_reg" in l)
i1 = next(i for i in range(i1, len(lines)) if lines[i] == "    }") + 1
ACCESSORS = '''    // Typed access to the generated register model, overlaid on the mapped
    // BAR0. The unsafety of the original read/write-volatile-at-offset helpers
    // is concentrated into these seven casts; all register access is typed.
    fn regs1(&self) -> &mut IntelIxgbeRegisters1 {
        assert!(self.size >= 0x20000, "BAR0 mapping smaller than register space");
        unsafe { &mut *(self.base as *mut IntelIxgbeRegisters1) }
    }
    fn rx1_regs(&self) -> &mut IntelIxgbeRxRegisters1 {
        unsafe { &mut *((self.base + 0x1000) as *mut IntelIxgbeRxRegisters1) }
    }
    fn regs2(&self) -> &mut IntelIxgbeRegisters2 {
        unsafe { &mut *((self.base + 0x2000) as *mut IntelIxgbeRegisters2) }
    }
    fn tx_regs(&self) -> &mut IntelIxgbeTxRegisters {
        unsafe { &mut *((self.base + 0x6000) as *mut IntelIxgbeTxRegisters) }
    }
    fn mac_regs(&self) -> &mut IntelIxgbeMacRegisters {
        unsafe { &mut *((self.base + 0x8000) as *mut IntelIxgbeMacRegisters) }
    }
    fn regs3(&self) -> &mut IntelIxgbeRegisters3 {
        unsafe { &mut *((self.base + 0xE000) as *mut IntelIxgbeRegisters3) }
    }
    /// Poll until `done` (100 ms interval), replacing wait_clear/write_reg.
    fn wait_until(&self, mut done: impl FnMut() -> bool) {
        loop {
            if done() {
                break;
            }
            thread::sleep(Duration::from_millis(100));
        }
    }'''
s = "\n".join(lines[:i0] + [ACCESSORS] + lines[i1:])

Q = r"u32::from\(queue_id\)"

s = sub(s, r"self\.write_reg\(IXGBE_RDT\(0\), self\.receive_index as u32\);",
        "self.rx1_regs().rx_regs1[0].rdt.write(self.receive_index as u32);")
s = sub(s, r"self\.write_reg\(IXGBE_TDT\(0\), self\.transmit_index as u32\);",
        "self.tx_regs().tx_regs[0].tdt.write(self.transmit_index as u32);")
s = sub(s, r"let icr = self\.read_reg\(IXGBE_EICR\);",
        "let icr = self.regs1().eicr.read();")
# MAC address: normalized from the legacy 0x5400 alias to the documented 0xA200 bank
s = sub(s, r"let low = self\.read_reg\(IXGBE_RAL\(0\)\);",
        "let low = self.mac_regs().ral.read();")
s = sub(s, r"let high = self\.read_reg\(IXGBE_RAH\(0\)\);",
        "let high = self.mac_regs().rah.read();")
s = sub(s, r"self\.write_reg\(IXGBE_RAL\(0\), low\);", "self.mac_regs().ral.write(low);")
s = sub(s, r"self\.write_reg\(IXGBE_RAH\(0\), high\);", "self.mac_regs().rah.write(high);")

s = sub(s, r"self\.write_reg\(IXGBE_EIMC, 0x7fff_ffff\);",
        "self.regs1().eimc.write(0x7fff_ffff);", count=2)
s = sub(s, r"self\.write_reg\(IXGBE_CTRL, IXGBE_CTRL_RST_MASK\);",
        "self.regs1().ctrl.write(IXGBE_CTRL_RST_MASK);")
s = sub(s, r"self\.wait_clear_reg\(IXGBE_CTRL, IXGBE_CTRL_RST_MASK\);",
        "self.wait_until(|| self.regs1().ctrl.read() & IXGBE_CTRL_RST_MASK == 0);")
s = sub(s, r"self\.wait_write_reg\(IXGBE_EEC, IXGBE_EEC_ARD\);",
        "self.wait_until(|| self.regs3().eec.read() & IXGBE_EEC_ARD != 0);")
s = sub(s, r"self\.wait_write_reg\(\s*IXGBE_RDRXCTL,\s*IXGBE_RDRXCTL_DMAIDONE \| IXGBE_RDRXCTL_RESERVED_BITS,\s*\);",
        "self.wait_until(|| {\n"
        "            let want = IXGBE_RDRXCTL_DMAIDONE | IXGBE_RDRXCTL_RESERVED_BITS;\n"
        "            self.regs2().rdrxctl.read() & want == want\n"
        "        });", flags=re.S)
for reg in ("gprc", "gptc", "gorcl", "gorch", "gotcl", "gotch"):
    s = sub(s, r"self\.read_reg\(IXGBE_" + reg.upper() + r"\);",
            f"self.regs2().{reg}.read();")

# init_rx: RXEN witness window
s = sub(s, r"self\.clear_flag\(IXGBE_RXCTRL, IXGBE_RXCTRL_RXEN\);",
        "// Gate: receive filters may only be modified while RXCTRL.RXEN = 0b\n"
        "        let rx_disabled = RxctrlRxenCleared::establish(&mut self.regs2().rxctrl);")
s = sub(s, r"self\.write_reg\(IXGBE_RXPBSIZE\(0\), IXGBE_RXPBSIZE_128KB\);",
        "self.regs2().rxpbsize[0].write(IXGBE_RXPBSIZE_128KB);")
s = sub(s, r"self\.write_reg\(IXGBE_RXPBSIZE\(i\), 0\);",
        "self.regs2().rxpbsize[i as usize].write(0);")
s = sub(s, r"self\.write_flag\(IXGBE_HLREG0, IXGBE_HLREG0_RXCRCSTRP\);\s*\n\s*self\.write_flag\(IXGBE_RDRXCTL, IXGBE_RDRXCTL_CRCSTRIP\);",
        "// Coupled relation: HLREG0.RXCRCSTRP must equal RDRXCTL.CRCStrip\n"
        "        {\n"
        "            let r2 = self.regs2();\n"
        "            set_rxcrcstrp_crcstrip(&mut r2.hlreg0, &mut r2.rdrxctl, true);\n"
        "        }")
s = sub(s, r"self\.write_flag\(IXGBE_FCTRL, IXGBE_FCTRL_BAM\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = r2.fctrl.read() | IXGBE_FCTRL_BAM;\n"
        "            r2.fctrl.write(v, &rx_disabled);\n"
        "        }")
s = sub(s, r"self\.write_reg\(\s*IXGBE_SRRCTL\(i\),\s*\(self\.read_reg\(IXGBE_SRRCTL\(i\)\) & !IXGBE_SRRCTL_DESCTYPE_MASK\)\s*\| IXGBE_SRRCTL_DESCTYPE_ADV_ONEBUF,\s*\);",
        "{\n"
        "            let srrctl = &mut self.rx1_regs().rx_regs1[i as usize].srrctl;\n"
        "            let v = (srrctl.read() & !IXGBE_SRRCTL_DESCTYPE_MASK) | IXGBE_SRRCTL_DESCTYPE_ADV_ONEBUF;\n"
        "            srrctl.write(v);\n"
        "        }", flags=re.S)
s = sub(s, r"self\.write_flag\(IXGBE_SRRCTL\(i\), IXGBE_SRRCTL_DROP_EN\);",
        "{\n"
        "            let srrctl = &mut self.rx1_regs().rx_regs1[i as usize].srrctl;\n"
        "            let v = srrctl.read() | IXGBE_SRRCTL_DROP_EN;\n"
        "            srrctl.write(v);\n"
        "        }")
s = sub(s, r"self\.write_reg\(IXGBE_RDBAL\(i\), self\.receive_ring\.physical\(\) as u32\);",
        "self.rx1_regs().rx_regs1[i as usize].rdbal.write(self.receive_ring.physical() as u32);")
s = sub(s, r"self\.write_reg\(\s*IXGBE_RDBAH\(i\),\s*\(\(self\.receive_ring\.physical\(\) as u64\) >> 32\) as u32,\s*\);",
        "self.rx1_regs().rx_regs1[i as usize].rdbah.write(((self.receive_ring.physical() as u64) >> 32) as u32);",
        flags=re.S)
s = sub(s, r"self\.write_reg\(\s*IXGBE_RDLEN\(i\),\s*\(self\.receive_ring\.len\(\) \* size_of::<ixgbe_adv_rx_desc>\(\)\) as u32,\s*\);",
        "self.rx1_regs().rx_regs1[i as usize].rdlen.write((self.receive_ring.len() * size_of::<ixgbe_adv_rx_desc>()) as u32);",
        flags=re.S)
s = sub(s, r"self\.write_reg\(IXGBE_RDH\(i\), 0\);",
        "self.rx1_regs().rx_regs1[i as usize].rdh.write(0);")
s = sub(s, r"self\.write_reg\(IXGBE_RDT\(i\), 0\);",
        "self.rx1_regs().rx_regs1[i as usize].rdt.write(0);")
s = sub(s, r"self\.write_flag\(IXGBE_CTRL_EXT, IXGBE_CTRL_EXT_NS_DIS\);",
        "{\n"
        "            let r1 = self.regs1();\n"
        "            let v = r1.ctrl_ext.read() | IXGBE_CTRL_EXT_NS_DIS;\n"
        "            r1.ctrl_ext.write(v);\n"
        "        }")
s = sub(s, r"self\.clear_flag\(IXGBE_DCA_RXCTRL\(i\), 1 << 12\);",
        "{\n"
        "            let d = &mut self.rx1_regs().rx_regs1[i as usize].dca_rxctrl;\n"
        "            let v = d.read() & !(1 << 12);\n"
        "            d.write(v);\n"
        "        }")
s = sub(s, r"self\.write_flag\(IXGBE_RXCTRL, IXGBE_RXCTRL_RXEN\);",
        "// re-enable the receiver, consuming the witness\n"
        "        rx_disabled.release(&mut self.regs2().rxctrl);")

# init_tx
s = sub(s, r"self\.write_flag\(IXGBE_HLREG0, IXGBE_HLREG0_TXCRCEN \| IXGBE_HLREG0_TXPADEN\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = r2.hlreg0.read() | IXGBE_HLREG0_TXCRCEN | IXGBE_HLREG0_TXPADEN;\n"
        "            r2.hlreg0.write_preserving(v);\n"
        "        }")
s = sub(s, r"self\.write_reg\(IXGBE_TXPBSIZE\(0\), IXGBE_TXPBSIZE_40KB\);",
        "self.mac_regs().txpbsize[0].write(IXGBE_TXPBSIZE_40KB);")
s = sub(s, r"self\.write_reg\(IXGBE_TXPBSIZE\(i\), 0\);",
        "self.mac_regs().txpbsize[i as usize].write(0);")
s = sub(s, r"self\.write_reg\(IXGBE_DTXMXSZRQ, 0xfff\);",
        "self.mac_regs().dtxmxszrq.write(0xfff);")
s = sub(s, r"self\.clear_flag\(IXGBE_RTTDCS, IXGBE_RTTDCS_ARBDIS\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = r2.rttdcs.read() & !IXGBE_RTTDCS_ARBDIS;\n"
        "            r2.rttdcs.write(v);\n"
        "        }")
s = sub(s, r"self\.write_reg\(IXGBE_TDBAL\(i\), self\.transmit_ring\.physical\(\) as u32\);",
        "self.tx_regs().tx_regs[i as usize].tdbal.write(self.transmit_ring.physical() as u32);")
s = sub(s, r"self\.write_reg\(\s*IXGBE_TDBAH\(i\),\s*\(\(self\.transmit_ring\.physical\(\) as u64\) >> 32\) as u32,\s*\);",
        "self.tx_regs().tx_regs[i as usize].tdbah.write(((self.transmit_ring.physical() as u64) >> 32) as u32);",
        flags=re.S)
s = sub(s, r"self\.write_reg\(\s*IXGBE_TDLEN\(i\),\s*\(self\.transmit_ring\.len\(\) \* size_of::<ixgbe_adv_tx_desc>\(\)\) as u32,\s*\);",
        "self.tx_regs().tx_regs[i as usize].tdlen.write((self.transmit_ring.len() * size_of::<ixgbe_adv_tx_desc>()) as u32);",
        flags=re.S)
s = sub(s, r"let mut txdctl = self\.read_reg\(IXGBE_TXDCTL\(i\)\);",
        "let mut txdctl = self.tx_regs().tx_regs[i as usize].txdctl.read();")
s = sub(s, r"self\.write_reg\(IXGBE_TXDCTL\(i\), txdctl\);",
        "self.tx_regs().tx_regs[i as usize].txdctl.write(txdctl);")
s = sub(s, r"self\.write_reg\(IXGBE_DMATXCTL, IXGBE_DMATXCTL_TE\);",
        "// hold-encoding: DMATXCTL.VT must not change — preserved by construction\n"
        "        // (the raw absolute write zeroed it, as in ixy)\n"
        "        self.regs2().dmatxctl.write_preserving(IXGBE_DMATXCTL_TE);")

# queue start
s = sub(s, r"self\.write_flag\(IXGBE_RXDCTL\(" + Q + r"\), IXGBE_RXDCTL_ENABLE\);",
        "{\n"
        "            let rxdctl = &mut self.rx1_regs().rx_regs1[usize::from(queue_id)].rxdctl;\n"
        "            let v = rxdctl.read() | IXGBE_RXDCTL_ENABLE;\n"
        "            rxdctl.write(v);\n"
        "        }")
s = sub(s, r"self\.wait_write_reg\(IXGBE_RXDCTL\(" + Q + r"\), IXGBE_RXDCTL_ENABLE\);",
        "self.wait_until(|| self.rx1_regs().rx_regs1[usize::from(queue_id)].rxdctl.read() & IXGBE_RXDCTL_ENABLE != 0);")
s = sub(s, r"self\.write_reg\(IXGBE_RDH\(" + Q + r"\), 0\);",
        "self.rx1_regs().rx_regs1[usize::from(queue_id)].rdh.write(0);")
s = sub(s, r"self\.write_reg\(\s*IXGBE_RDT\(" + Q + r"\),\s*\(self\.receive_ring\.len\(\) - 1\) as u32,\s*\);",
        "self.rx1_regs().rx_regs1[usize::from(queue_id)].rdt.write((self.receive_ring.len() - 1) as u32);",
        flags=re.S)
s = sub(s, r"self\.write_reg\(IXGBE_TDH\(" + Q + r"\), 0\);",
        "// Gate: TDH is writable only while the queue is disabled; minting the\n"
        "        // witness clears TXDCTL.ENABLE (a no-op here, before enable)\n"
        "        {\n"
        "            let txq = &mut self.tx_regs().tx_regs[usize::from(queue_id)];\n"
        "            let witness = TxdctlEnableCleared::establish(&mut txq.txdctl);\n"
        "            txq.tdh.write(0, &witness);\n"
        "        }")
s = sub(s, r"self\.write_reg\(IXGBE_TDT\(" + Q + r"\), 0\);",
        "self.tx_regs().tx_regs[usize::from(queue_id)].tdt.write(0);")
s = sub(s, r"self\.write_flag\(IXGBE_TXDCTL\(" + Q + r"\), IXGBE_TXDCTL_ENABLE\);",
        "{\n"
        "            let txdctl = &mut self.tx_regs().tx_regs[usize::from(queue_id)].txdctl;\n"
        "            let v = txdctl.read() | IXGBE_TXDCTL_ENABLE;\n"
        "            txdctl.write(v);\n"
        "        }")
s = sub(s, r"self\.wait_write_reg\(IXGBE_TXDCTL\(" + Q + r"\), IXGBE_TXDCTL_ENABLE\);",
        "self.wait_until(|| self.tx_regs().tx_regs[usize::from(queue_id)].txdctl.read() & IXGBE_TXDCTL_ENABLE != 0);")

# link setup
s = sub(s, r"self\.write_reg\(\s*IXGBE_AUTOC,\s*\(self\.read_reg\(IXGBE_AUTOC\) & !IXGBE_AUTOC_LMS_MASK\) \| IXGBE_AUTOC_LMS_10G_SERIAL,\s*\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = (r2.autoc.read() & !IXGBE_AUTOC_LMS_MASK) | IXGBE_AUTOC_LMS_10G_SERIAL;\n"
        "            r2.autoc.write(v);\n"
        "        }", flags=re.S)
s = sub(s, r"self\.write_reg\(\s*IXGBE_AUTOC,\s*\(self\.read_reg\(IXGBE_AUTOC\) & !IXGBE_AUTOC_10G_PMA_PMD_MASK\) \| IXGBE_AUTOC_10G_XAUI,\s*\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = (r2.autoc.read() & !IXGBE_AUTOC_10G_PMA_PMD_MASK) | IXGBE_AUTOC_10G_XAUI;\n"
        "            r2.autoc.write(v);\n"
        "        }", flags=re.S)
s = sub(s, r"self\.write_flag\(IXGBE_AUTOC, IXGBE_AUTOC_AN_RESTART\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = r2.autoc.read() | IXGBE_AUTOC_AN_RESTART;\n"
        "            r2.autoc.write(v);\n"
        "        }")

# promiscuous: previously toggled FCTRL with the receiver live — now witnessed
s = sub(s, r"self\.write_flag\(IXGBE_FCTRL, IXGBE_FCTRL_MPE \| IXGBE_FCTRL_UPE\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let rx_off = RxctrlRxenCleared::establish(&mut r2.rxctrl);\n"
        "            let v = r2.fctrl.read() | IXGBE_FCTRL_MPE | IXGBE_FCTRL_UPE;\n"
        "            r2.fctrl.write(v, &rx_off);\n"
        "            rx_off.release(&mut r2.rxctrl);\n"
        "        }")
s = sub(s, r"self\.clear_flag\(IXGBE_FCTRL, IXGBE_FCTRL_MPE \| IXGBE_FCTRL_UPE\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let rx_off = RxctrlRxenCleared::establish(&mut r2.rxctrl);\n"
        "            let v = r2.fctrl.read() & !(IXGBE_FCTRL_MPE | IXGBE_FCTRL_UPE);\n"
        "            r2.fctrl.write(v, &rx_off);\n"
        "            rx_off.release(&mut r2.rxctrl);\n"
        "        }")

# interrupts
s = sub(s, r"let mut ivar = self\.read_reg\(IXGBE_IVAR\(u32::from\(queue_id >> 1\)\)\);",
        "let mut ivar = self.regs1().ivar[usize::from(queue_id >> 1)].read();")
s = sub(s, r"self\.write_reg\(IXGBE_IVAR\(u32::from\(queue_id >> 1\)\), ivar\);",
        "self.regs1().ivar[usize::from(queue_id >> 1)].write(ivar);")
s = sub(s, r"self\.write_reg\(IXGBE_EIAC, IXGBE_EICR_RTX_QUEUE\);",
        "// clamp-encoding: the shared-MSI-X bits can never be set here\n"
        "        self.regs1().eiac.write_preserving(IXGBE_EICR_RTX_QUEUE);")
s = sub(s, r"let mut mask: u32 = self\.read_reg\(IXGBE_EIMS\);",
        "let mut mask: u32 = self.regs1().eims.read();")
s = sub(s, r"self\.write_reg\(IXGBE_EIMS, mask\);",
        "self.regs1().eims.write(mask);")
s = sub(s, r"let speed = self\.read_reg\(IXGBE_LINKS\);",
        "let speed = self.regs2().links.read();")

open(p, "w").write(s)
print(f"port applied: {n_subs} replacements")
