#!/usr/bin/env python3
"""Retrofit demonstration: port ixy.rs onto the generated 82599 HAL.

Applies the full mechanical port to the (gitignored) clone in clones/ixy.rs:
  - installs the generated gated HAL (hal_out/<run>-gated-plain/regs.rs)
  - replaces ixy's 6 offset-based MMIO helpers with 7 typed region accessors
    over its mapped BAR0 (same unsafety, now concentrated in 7 casts)
  - rewrites every register access site to typed struct access, threading the
    constraint witnesses (RXCTRL/FCTRL, TXDCTL/TDH, CRC-strip coupling, EIAC
    clamp, DMATXCTL hold)
Every replacement is asserted; run idempotence is NOT attempted — re-clone to
re-run. Usage: python3 port_ixy.py [run_tag]   (default r006)
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = sys.argv[1] if len(sys.argv) > 1 else "r006"
IXY = os.path.join(HERE, "clones", "ixy.rs")
HAL = os.path.join(HERE, "..", "pipeline", "hal_out", f"{RUN}-gated-plain", "regs.rs")

n_subs = 0


def sub(src, pattern, repl, count=1, flags=0):
    global n_subs
    new, n = re.subn(pattern, repl, src, flags=flags)
    assert n == count, f"pattern matched {n} times (wanted {count}): {pattern[:80]}"
    n_subs += n
    return new


# 1) install the HAL + dependency + module
shutil.copy(HAL, os.path.join(IXY, "src", "regs.rs"))
p = os.path.join(IXY, "Cargo.toml")
s = open(p).read()
if "volatile" not in s:
    s = sub(s, r"\[dependencies\]", "[dependencies]\nvolatile = \"0.2\"")
open(p, "w").write(s)
p = os.path.join(IXY, "src", "lib.rs")
s = open(p).read()
if "pub mod regs;" not in s:
    s = sub(s, r"(pub mod memory;)", r"\1\npub mod regs;")
open(p, "w").write(s)

# 2) ixgbe.rs
p = os.path.join(IXY, "src", "ixgbe.rs")
s = open(p).read()
s = sub(s, r"(use crate::memory::\*;)", r"\1\nuse crate::regs::*;")

# replace the offset-helper block (get_reg32 .. wait_set_reg32) with typed accessors
lines = s.split("\n")
i0 = next(i for i, l in enumerate(lines) if "fn get_reg32(&self, reg: u32)" in l)
# back up over the doc comment/attribute lines
while lines[i0 - 1].strip().startswith(("///", "#[")):
    i0 -= 1
i1 = next(i for i, l in enumerate(lines) if "fn wait_set_reg32" in l)
i1 = next(i for i in range(i1, len(lines)) if lines[i] == "    }") + 1
ACCESSORS = '''    // Typed access to the generated register model, overlaid on the mapped
    // BAR0. The unsafety of ixy's original ptr::read/write_volatile-at-offset
    // helpers is concentrated into these seven casts; all register access is
    // typed (offsets, widths, RO/WO, arrays, padding, size asserts, gates).
    fn regs1(&self) -> &mut IntelIxgbeRegisters1 {
        assert!(self.len >= 0x20000);
        unsafe { &mut *(self.addr as *mut IntelIxgbeRegisters1) }
    }
    fn rx1_regs(&self) -> &mut IntelIxgbeRxRegisters1 {
        unsafe { &mut *(self.addr.add(0x1000) as *mut IntelIxgbeRxRegisters1) }
    }
    fn regs2(&self) -> &mut IntelIxgbeRegisters2 {
        unsafe { &mut *(self.addr.add(0x2000) as *mut IntelIxgbeRegisters2) }
    }
    fn tx_regs(&self) -> &mut IntelIxgbeTxRegisters {
        unsafe { &mut *(self.addr.add(0x6000) as *mut IntelIxgbeTxRegisters) }
    }
    fn mac_regs(&self) -> &mut IntelIxgbeMacRegisters {
        unsafe { &mut *(self.addr.add(0x8000) as *mut IntelIxgbeMacRegisters) }
    }
    fn regs3(&self) -> &mut IntelIxgbeRegisters3 {
        unsafe { &mut *(self.addr.add(0xE000) as *mut IntelIxgbeRegisters3) }
    }
    /// Poll until `done` (10 ms interval), replacing wait_set/clear_reg32.
    fn wait_until(&self, mut done: impl FnMut() -> bool) {
        loop {
            if done() {
                break;
            }
            thread::sleep(Duration::from_millis(10));
        }
    }'''
s = "\n".join(lines[:i0] + [ACCESSORS] + lines[i1:])

Q = r"u32::from\(queue_id\)"
I = r"u32::from\(i\)"

# --- MAC address ---
s = sub(s, r"let low = self\.get_reg32\(IXGBE_RAL\(0\)\);",
        "let low = self.mac_regs().ral.read();")
s = sub(s, r"let high = self\.get_reg32\(IXGBE_RAH\(0\)\);",
        "let high = self.mac_regs().rah.read();")
s = sub(s, r"self\.set_reg32\(IXGBE_RAL\(0\), low\);", "self.mac_regs().ral.write(low);")
s = sub(s, r"self\.set_reg32\(IXGBE_RAH\(0\), high\);", "self.mac_regs().rah.write(high);")

# --- rx/tx tails ---
s = sub(s, r"self\.set_reg32\(IXGBE_RDT\(" + Q + r"\), last_rx_index as u32\);",
        "self.rx1_regs().rx_regs1[queue_id as usize].rdt.write(last_rx_index as u32);")
s = sub(s, r"self\.set_reg32\(\s*IXGBE_TDT\(" + Q + r"\),\s*self\.tx_queues\[queue_id as usize\]\.tx_index as u32,\s*\);",
        "self.tx_regs().tx_regs[queue_id as usize].tdt"
        ".write(self.tx_queues[queue_id as usize].tx_index as u32);", flags=re.S)

# --- stats (2 sites each) ---
for reg in ("gprc", "gptc", "gorcl", "gorch", "gotcl", "gotch"):
    s = sub(s, r"self\.get_reg32\(IXGBE_" + reg.upper() + r"\)",
            f"self.regs2().{reg}.read()", count=2)
s = sub(s, r"let speed = self\.get_reg32\(IXGBE_LINKS\);",
        "let speed = self.regs2().links.read();")

# --- reset + ready waits ---
s = sub(s, r"self\.set_reg32\(IXGBE_CTRL, IXGBE_CTRL_RST_MASK\);",
        "self.regs1().ctrl.write(IXGBE_CTRL_RST_MASK);")
s = sub(s, r"self\.wait_clear_reg32\(IXGBE_CTRL, IXGBE_CTRL_RST_MASK\);",
        "self.wait_until(|| self.regs1().ctrl.read() & IXGBE_CTRL_RST_MASK == 0);")
s = sub(s, r"self\.wait_set_reg32\(IXGBE_EEC, IXGBE_EEC_ARD\);",
        "self.wait_until(|| self.regs3().eec.read() & IXGBE_EEC_ARD != 0);")
s = sub(s, r"self\.wait_set_reg32\(IXGBE_RDRXCTL, IXGBE_RDRXCTL_DMAIDONE\);",
        "self.wait_until(|| self.regs2().rdrxctl.read() & IXGBE_RDRXCTL_DMAIDONE != 0);")

# --- init_rx: witness window (RXEN cleared) around filter/config writes ---
s = sub(s, r"self\.clear_flags32\(IXGBE_RXCTRL, IXGBE_RXCTRL_RXEN\);",
        "// Gate: receive filters may only be modified while RXCTRL.RXEN = 0b\n"
        "        let rx_disabled = RxctrlRxenCleared::establish(&mut self.regs2().rxctrl);")
s = sub(s, r"self\.set_reg32\(IXGBE_RXPBSIZE\(0\), IXGBE_RXPBSIZE_128KB\);",
        "self.regs2().rxpbsize[0].write(IXGBE_RXPBSIZE_128KB);")
s = sub(s, r"self\.set_reg32\(IXGBE_RXPBSIZE\(i\), 0\);",
        "self.regs2().rxpbsize[i as usize].write(0);")
s = sub(s, r"self\.set_flags32\(IXGBE_HLREG0, IXGBE_HLREG0_RXCRCSTRP\);\s*\n\s*self\.set_flags32\(IXGBE_RDRXCTL, IXGBE_RDRXCTL_CRCSTRIP\);",
        "// Coupled relation: HLREG0.RXCRCSTRP must equal RDRXCTL.CRCStrip\n"
        "        {\n"
        "            let r2 = self.regs2();\n"
        "            set_rxcrcstrp_crcstrip(&mut r2.hlreg0, &mut r2.rdrxctl, true);\n"
        "        }")
s = sub(s, r"self\.clear_flags32\(IXGBE_RDRXCTL, IXGBE_RDRXCTL_RSCFRSTSIZE\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = r2.rdrxctl.read() & !IXGBE_RDRXCTL_RSCFRSTSIZE;\n"
        "            r2.rdrxctl.write_preserving(v);\n"
        "        }")
s = sub(s, r"let rdrxctl = self\.get_reg32\(IXGBE_RDRXCTL\);",
        "let rdrxctl = self.regs2().rdrxctl.read();")
s = sub(s, r"self\.set_reg32\(IXGBE_RDRXCTL, rdrxctl & !IXGBE_RDRXCTL_RSCFRSTSIZE \| IXGBE_RDRXCTL_RSCACKC \| IXGBE_RDRXCTL_FCOE_WRFIX\);",
        "self.regs2().rdrxctl.write_preserving(rdrxctl & !IXGBE_RDRXCTL_RSCFRSTSIZE | IXGBE_RDRXCTL_RSCACKC | IXGBE_RDRXCTL_FCOE_WRFIX);")
s = sub(s, r"self\.set_flags32\(IXGBE_FCTRL, IXGBE_FCTRL_BAM\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = r2.fctrl.read() | IXGBE_FCTRL_BAM;\n"
        "            r2.fctrl.write(v, &rx_disabled);\n"
        "        }")
s = sub(s, r"self\.set_reg32\(\s*IXGBE_SRRCTL\(" + I + r"\),\s*\(self\.get_reg32\(IXGBE_SRRCTL\(" + I + r"\)\) & !IXGBE_SRRCTL_DESCTYPE_MASK\)\s*\| IXGBE_SRRCTL_DESCTYPE_ADV_ONEBUF,\s*\);",
        "{\n"
        "                let srrctl = &mut self.rx1_regs().rx_regs1[i as usize].srrctl;\n"
        "                let v = (srrctl.read() & !IXGBE_SRRCTL_DESCTYPE_MASK) | IXGBE_SRRCTL_DESCTYPE_ADV_ONEBUF;\n"
        "                srrctl.write(v);\n"
        "            }", flags=re.S)
s = sub(s, r"self\.set_flags32\(IXGBE_SRRCTL\(" + I + r"\), IXGBE_SRRCTL_DROP_EN\);",
        "{\n"
        "                let srrctl = &mut self.rx1_regs().rx_regs1[i as usize].srrctl;\n"
        "                let v = srrctl.read() | IXGBE_SRRCTL_DROP_EN;\n"
        "                srrctl.write(v);\n"
        "            }")
s = sub(s, r"self\.set_reg32\(\s*IXGBE_RDBAL\(" + I + r"\),\s*\(dma\.phys as u64 & 0xffff_ffff\) as u32,\s*\);",
        "self.rx1_regs().rx_regs1[i as usize].rdbal.write((dma.phys as u64 & 0xffff_ffff) as u32);",
        flags=re.S)
s = sub(s, r"self\.set_reg32\(IXGBE_RDBAH\(" + I + r"\), \(dma\.phys as u64 >> 32\) as u32\);",
        "self.rx1_regs().rx_regs1[i as usize].rdbah.write((dma.phys as u64 >> 32) as u32);")
s = sub(s, r"self\.set_reg32\(IXGBE_RDLEN\(" + I + r"\), ring_size_bytes as u32\);",
        "self.rx1_regs().rx_regs1[i as usize].rdlen.write(ring_size_bytes as u32);")
s = sub(s, r"self\.set_reg32\(IXGBE_RDH\(" + I + r"\), 0\);",
        "self.rx1_regs().rx_regs1[i as usize].rdh.write(0);")
s = sub(s, r"self\.set_reg32\(IXGBE_RDT\(" + I + r"\), 0\);",
        "self.rx1_regs().rx_regs1[i as usize].rdt.write(0);")
s = sub(s, r"self\.set_flags32\(IXGBE_CTRL_EXT, IXGBE_CTRL_EXT_NS_DIS\);",
        "{\n"
        "            let r1 = self.regs1();\n"
        "            let v = r1.ctrl_ext.read() | IXGBE_CTRL_EXT_NS_DIS;\n"
        "            r1.ctrl_ext.write(v);\n"
        "        }")
s = sub(s, r"self\.clear_flags32\(IXGBE_DCA_RXCTRL\(" + I + r"\), 1 << 12\);",
        "{\n"
        "                let d = &mut self.rx1_regs().rx_regs1[i as usize].dca_rxctrl;\n"
        "                let v = d.read() & !(1 << 12);\n"
        "                d.write(v);\n"
        "            }")
s = sub(s, r"self\.set_flags32\(IXGBE_RXCTRL, IXGBE_RXCTRL_RXEN\);",
        "// re-enable the receiver, consuming the proof\n"
        "        rx_disabled.release(&mut self.regs2().rxctrl);")

# --- init_tx ---
s = sub(s, r"self\.set_flags32\(IXGBE_HLREG0, IXGBE_HLREG0_TXCRCEN \| IXGBE_HLREG0_TXPADEN\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = r2.hlreg0.read() | IXGBE_HLREG0_TXCRCEN | IXGBE_HLREG0_TXPADEN;\n"
        "            r2.hlreg0.write_preserving(v);\n"
        "        }")
s = sub(s, r"self\.set_reg32\(IXGBE_TXPBSIZE\(0\), IXGBE_TXPBSIZE_40KB\);",
        "self.mac_regs().txpbsize[0].write(IXGBE_TXPBSIZE_40KB);")
s = sub(s, r"self\.set_reg32\(IXGBE_TXPBSIZE\(i\), 0\);",
        "self.mac_regs().txpbsize[i as usize].write(0);")
s = sub(s, r"self\.set_reg32\(IXGBE_DTXMXSZRQ, 0xfff\);",
        "self.mac_regs().dtxmxszrq.write(0xfff);")
s = sub(s, r"self\.clear_flags32\(IXGBE_RTTDCS, IXGBE_RTTDCS_ARBDIS\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = r2.rttdcs.read() & !IXGBE_RTTDCS_ARBDIS;\n"
        "            r2.rttdcs.write(v);\n"
        "        }")
s = sub(s, r"self\.set_reg32\(\s*IXGBE_TDBAL\(" + I + r"\),\s*\(dma\.phys as u64 & 0xffff_ffff\) as u32,\s*\);",
        "self.tx_regs().tx_regs[i as usize].tdbal.write((dma.phys as u64 & 0xffff_ffff) as u32);",
        flags=re.S)
s = sub(s, r"self\.set_reg32\(IXGBE_TDBAH\(" + I + r"\), \(dma\.phys as u64 >> 32\) as u32\);",
        "self.tx_regs().tx_regs[i as usize].tdbah.write((dma.phys as u64 >> 32) as u32);")
s = sub(s, r"self\.set_reg32\(IXGBE_TDLEN\(" + I + r"\), ring_size_bytes as u32\);",
        "self.tx_regs().tx_regs[i as usize].tdlen.write(ring_size_bytes as u32);")
s = sub(s, r"let mut txdctl = self\.get_reg32\(IXGBE_TXDCTL\(" + I + r"\)\);",
        "let mut txdctl = self.tx_regs().tx_regs[i as usize].txdctl.read();")
s = sub(s, r"self\.set_reg32\(IXGBE_TXDCTL\(" + I + r"\), txdctl\);",
        "self.tx_regs().tx_regs[i as usize].txdctl.write(txdctl);")
s = sub(s, r"self\.set_reg32\(IXGBE_DMATXCTL, IXGBE_DMATXCTL_TE\);",
        "// hold-encoding: DMATXCTL.VT must not change — preserved by construction\n"
        "        // (ixy's raw absolute write zeroed it)\n"
        "        self.regs2().dmatxctl.write_preserving(IXGBE_DMATXCTL_TE);")

# --- queue start ---
s = sub(s, r"self\.set_flags32\(IXGBE_RXDCTL\(" + Q + r"\), IXGBE_RXDCTL_ENABLE\);",
        "{\n"
        "            let rxdctl = &mut self.rx1_regs().rx_regs1[queue_id as usize].rxdctl;\n"
        "            let v = rxdctl.read() | IXGBE_RXDCTL_ENABLE;\n"
        "            rxdctl.write(v);\n"
        "        }")
s = sub(s, r"self\.wait_set_reg32\(IXGBE_RXDCTL\(" + Q + r"\), IXGBE_RXDCTL_ENABLE\);",
        "self.wait_until(|| self.rx1_regs().rx_regs1[queue_id as usize].rxdctl.read() & IXGBE_RXDCTL_ENABLE != 0);")
s = sub(s, r"self\.set_reg32\(IXGBE_RDH\(" + Q + r"\), 0\);",
        "self.rx1_regs().rx_regs1[queue_id as usize].rdh.write(0);")
s = sub(s, r"self\.set_reg32\(\s*IXGBE_RDT\(" + Q + r"\),\s*\(queue\.num_descriptors - 1\) as u32,\s*\);",
        "self.rx1_regs().rx_regs1[queue_id as usize].rdt.write((queue.num_descriptors - 1) as u32);",
        flags=re.S)
s = sub(s, r"self\.set_reg32\(IXGBE_TDH\(" + Q + r"\), 0\);",
        "// Gate: TDH is writable only while the queue is disabled; minting the\n"
        "        // proof clears TXDCTL.ENABLE (a no-op here, before enable)\n"
        "        {\n"
        "            let txq = &mut self.tx_regs().tx_regs[queue_id as usize];\n"
        "            let proof = TxdctlEnableCleared::establish(&mut txq.txdctl);\n"
        "            txq.tdh.write(0, &proof);\n"
        "        }")
s = sub(s, r"self\.set_reg32\(IXGBE_TDT\(" + Q + r"\), 0\);",
        "self.tx_regs().tx_regs[queue_id as usize].tdt.write(0);")
s = sub(s, r"self\.set_flags32\(IXGBE_TXDCTL\(" + Q + r"\), IXGBE_TXDCTL_ENABLE\);",
        "{\n"
        "            let txdctl = &mut self.tx_regs().tx_regs[queue_id as usize].txdctl;\n"
        "            let v = txdctl.read() | IXGBE_TXDCTL_ENABLE;\n"
        "            txdctl.write(v);\n"
        "        }")
s = sub(s, r"self\.wait_set_reg32\(IXGBE_TXDCTL\(" + Q + r"\), IXGBE_TXDCTL_ENABLE\);",
        "self.wait_until(|| self.tx_regs().tx_regs[queue_id as usize].txdctl.read() & IXGBE_TXDCTL_ENABLE != 0);")

# --- link setup ---
s = sub(s, r"self\.set_reg32\(\s*IXGBE_AUTOC,\s*\(self\.get_reg32\(IXGBE_AUTOC\) & !IXGBE_AUTOC_LMS_MASK\) \| IXGBE_AUTOC_LMS_10G_SERIAL,\s*\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = (r2.autoc.read() & !IXGBE_AUTOC_LMS_MASK) | IXGBE_AUTOC_LMS_10G_SERIAL;\n"
        "            r2.autoc.write(v);\n"
        "        }", flags=re.S)
s = sub(s, r"self\.set_reg32\(\s*IXGBE_AUTOC,\s*\(self\.get_reg32\(IXGBE_AUTOC\) & !IXGBE_AUTOC_10G_PMA_PMD_MASK\) \| IXGBE_AUTOC_10G_XAUI,\s*\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = (r2.autoc.read() & !IXGBE_AUTOC_10G_PMA_PMD_MASK) | IXGBE_AUTOC_10G_XAUI;\n"
        "            r2.autoc.write(v);\n"
        "        }", flags=re.S)
s = sub(s, r"self\.set_flags32\(IXGBE_AUTOC, IXGBE_AUTOC_AN_RESTART\);",
        "{\n"
        "            let r2 = self.regs2();\n"
        "            let v = r2.autoc.read() | IXGBE_AUTOC_AN_RESTART;\n"
        "            r2.autoc.write(v);\n"
        "        }")

# --- promiscuous: the gate exposes that ixy modified filters with RXEN live ---
s = sub(s, r"self\.set_flags32\(IXGBE_FCTRL, IXGBE_FCTRL_MPE \| IXGBE_FCTRL_UPE\);",
        "{\n"
        "                let r2 = self.regs2();\n"
        "                let rx_off = RxctrlRxenCleared::establish(&mut r2.rxctrl);\n"
        "                let v = r2.fctrl.read() | IXGBE_FCTRL_MPE | IXGBE_FCTRL_UPE;\n"
        "                r2.fctrl.write(v, &rx_off);\n"
        "                rx_off.release(&mut r2.rxctrl);\n"
        "            }")
s = sub(s, r"self\.clear_flags32\(IXGBE_FCTRL, IXGBE_FCTRL_MPE \| IXGBE_FCTRL_UPE\);",
        "{\n"
        "                let r2 = self.regs2();\n"
        "                let rx_off = RxctrlRxenCleared::establish(&mut r2.rxctrl);\n"
        "                let v = r2.fctrl.read() & !(IXGBE_FCTRL_MPE | IXGBE_FCTRL_UPE);\n"
        "                r2.fctrl.write(v, &rx_off);\n"
        "                rx_off.release(&mut r2.rxctrl);\n"
        "            }")

# --- interrupts ---
s = sub(s, r"ivar = self\.get_reg32\(IXGBE_IVAR\(u32::from\(queue\) >> 1\)\);",
        "ivar = self.regs1().ivar[(u32::from(queue) >> 1) as usize].read();")
s = sub(s, r"self\.set_reg32\(IXGBE_IVAR\(u32::from\(queue\) >> 1\), ivar\);",
        "self.regs1().ivar[(u32::from(queue) >> 1) as usize].write(ivar);")
s = sub(s, r"self\.set_reg32\(IXGBE_EIMC, IXGBE_IRQ_CLEAR_MASK\);",
        "self.regs1().eimc.write(IXGBE_IRQ_CLEAR_MASK);")
s = sub(s, r"self\.set_reg32\(IXGBE_EIMC, 1 << queue_id\);",
        "self.regs1().eimc.write(1 << queue_id);")
s = sub(s, r"self\.get_reg32\(IXGBE_EICR\);", "self.regs1().eicr.read();", count=2)
s = sub(s, r"self\.set_reg32\(IXGBE_EIMS, 0x0000_0000\);",
        "self.regs1().eims.write(0x0000_0000);")
s = sub(s, r"let mut mask: u32 = self\.get_reg32\(IXGBE_EIMS\);",
        "let mut mask: u32 = self.regs1().eims.read();", count=3)
s = sub(s, r"self\.set_reg32\(IXGBE_EIMS, mask\);",
        "self.regs1().eims.write(mask);", count=3)
s = sub(s, r"self\.set_reg32\(IXGBE_EIAC, 0x0000_0000\);",
        "self.regs1().eiac.write_preserving(0x0000_0000);")
s = sub(s, r"self\.set_reg32\(IXGBE_EIAC, IXGBE_EIMS_RTX_QUEUE\);",
        "// clamp-encoding: the shared-MSI-X bits can never be set here\n"
        "        self.regs1().eiac.write_preserving(IXGBE_EIMS_RTX_QUEUE);")
s = sub(s, r"self\.set_reg32\(IXGBE_EITR\(" + Q + r"\), self\.interrupts\.itr_rate\);",
        "self.regs1().eitr[queue_id as usize].write(self.interrupts.itr_rate);", count=2)
s = sub(s, r"let mut gpie: u32 = self\.get_reg32\(IXGBE_GPIE\);",
        "let mut gpie: u32 = self.regs1().gpie.read();")
s = sub(s, r"self\.set_reg32\(IXGBE_GPIE, gpie\);",
        "self.regs1().gpie.write(gpie);")

open(p, "w").write(s)
print(f"port applied: {n_subs} replacements")
