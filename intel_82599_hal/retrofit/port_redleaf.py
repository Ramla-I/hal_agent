#!/usr/bin/env python3
"""Retrofit demonstration 3 (Tier A): retarget RedLeaf's ixgbe register layer
onto the generated 82599 HAL — enum API preserved, ZERO call-site changes.

RedLeaf funnels every register access through one enum-keyed layer
(IxgbeRegs scalars + IxgbeDmaArrayRegs/IxgbeNoDmaArrayRegs arrays). This port
replaces the layer's INTERNALS (raw base+offset volatile pointer math) with
typed access into the generated region structs. By construction this fixes
the layer's latent defects:
  - RDLEN declared with stride 0x60 (should be 0x40): for any queue > 0 the
    raw math wrote RXDCTL of that queue instead of RDLEN (dormant: RedLeaf
    uses queue 0)
  - STATUS = 0x00004 (that is CTRL's alias offset; STATUS is 0x8)
  - 64-bit volatile reads of 32-bit registers (read the neighbouring register
    too — a hazard next to read-to-clear registers)
  - SRRCTL/DCA_TXCTRL used legacy 82598-compat banks; normalized to the
    documented primary banks
Gates apply force-the-action style inside the layer (as in Theseus set_tdh):
writing Tdh establishes the queue-disabled witness; FCTRL writes establish/
release the RXEN window. Registers outside the 75-register model (19 stats
scalars, TxpbThresh, Qptc, Rxmpc, RAL/RAH beyond entry 0) keep the raw path,
now with correct 32-bit reads (each arm documented).

Every replacement asserted; not idempotent — re-clone to re-run.
Usage: python3 port_redleaf.py [run_tag]   (default r006)
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = sys.argv[1] if len(sys.argv) > 1 else "r006"
DRV = os.path.join(HERE, "clones", "redleaf", "lib", "devices", "ixgbe")
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

# ---- lib.rs: declare the module + retarget the two scalar helpers ----
p = os.path.join(DRV, "src", "lib.rs")
s = open(p).read()
s = sub(s, r"(mod ixgbe_regs;)", r"\1\npub mod regs;")
s = sub(s, r"(pub use ixgbe_regs::\{IxgbeRegs, IxgbeNoDmaArrayRegs\};)",
        r"\1\nuse ixgbe_regs::{regs1, regs2, regs3, mac_regs};")

OLD_SCALARS = '''    pub fn read_reg(&self, reg: IxgbeRegs) -> u64 {
        unsafe {
            ptr::read_volatile((self.bar.get_base() as u64 + reg as u64) as *const u64) & 0xFFFF_FFFF as u64
        }
    }

    pub fn write_reg(&self, reg: IxgbeRegs, val: u64) {
        unsafe {
            //println!("writing to {:x}", self.bar.get_base() as u64 + reg as u64);
            ptr::write_volatile((self.bar.get_base() as u64 + reg as u64) as *mut u32, val as u32);
        }
    }'''
NEW_SCALARS = '''    pub fn read_reg(&self, reg: IxgbeRegs) -> u64 {
        use crate::regs::*;
        u64::from(match reg {
            IxgbeRegs::CTRL => regs1(&self.bar).ctrl.read(),
            // enum discriminant was 0x4 (CTRL's alias offset); typed access
            // reads the actual STATUS register at 0x8
            IxgbeRegs::STATUS => regs1(&self.bar).status.read(),
            IxgbeRegs::CTRL_EXT => regs1(&self.bar).ctrl_ext.read(),
            IxgbeRegs::EEC => regs3(&self.bar).eec.read(),
            IxgbeRegs::AUTOC => regs2(&self.bar).autoc.read(),
            IxgbeRegs::GPRC => regs2(&self.bar).gprc.read(),
            IxgbeRegs::GPTC => regs2(&self.bar).gptc.read(),
            IxgbeRegs::GORCL => regs2(&self.bar).gorcl.read(),
            IxgbeRegs::GORCH => regs2(&self.bar).gorch.read(),
            IxgbeRegs::GOTCL => regs2(&self.bar).gotcl.read(),
            IxgbeRegs::GOTCH => regs2(&self.bar).gotch.read(),
            IxgbeRegs::HLREG0 => regs2(&self.bar).hlreg0.read(),
            IxgbeRegs::LINKS => regs2(&self.bar).links.read(),
            IxgbeRegs::FCTRL => regs2(&self.bar).fctrl.read(),
            IxgbeRegs::RXCTRL => regs2(&self.bar).rxctrl.read(),
            IxgbeRegs::RDRXCTL => regs2(&self.bar).rdrxctl.read(),
            IxgbeRegs::DTXMXSZRQ => mac_regs(&self.bar).dtxmxszrq.read(),
            IxgbeRegs::DMATXCTL => regs2(&self.bar).dmatxctl.read(),
            IxgbeRegs::RTTDCS => regs2(&self.bar).rttdcs.read(),
            IxgbeRegs::EICR => regs1(&self.bar).eicr.read(),
            IxgbeRegs::EIMS => regs1(&self.bar).eims.read(),
            IxgbeRegs::EIMC => 0, // write-only register; raw read returned junk
            IxgbeRegs::EIAC => regs1(&self.bar).eiac.read(),
            IxgbeRegs::GPIE => regs1(&self.bar).gpie.read(),
            // statistics registers outside the generated model: raw path,
            // now a correct 32-bit volatile read (was a 64-bit read spanning
            // the neighbouring register)
            other => unsafe {
                ptr::read_volatile((self.bar.get_base() as u64 + other as u64) as *const u32)
            },
        })
    }

    pub fn write_reg(&self, reg: IxgbeRegs, val: u64) {
        use crate::regs::*;
        let v = val as u32;
        match reg {
            IxgbeRegs::CTRL => regs1(&self.bar).ctrl.write(v),
            IxgbeRegs::CTRL_EXT => regs1(&self.bar).ctrl_ext.write(v),
            IxgbeRegs::AUTOC => regs2(&self.bar).autoc.write(v),
            // Gate: receive filters may only be modified while RXCTRL.RXEN=0b;
            // force-the-action: establish (clears RXEN), write, release
            IxgbeRegs::FCTRL => {
                let r2 = regs2(&self.bar);
                let rx_off = RxctrlRxenCleared::establish(&mut r2.rxctrl);
                r2.fctrl.write(v, &rx_off);
                rx_off.release(&mut r2.rxctrl);
            }
            IxgbeRegs::RXCTRL => regs2(&self.bar).rxctrl.write(v),
            // protected bits (CRC-strip coupling / VT hold / MSI-X clamp)
            IxgbeRegs::HLREG0 => regs2(&self.bar).hlreg0.write_preserving(v),
            IxgbeRegs::RDRXCTL => regs2(&self.bar).rdrxctl.write_preserving(v),
            IxgbeRegs::DMATXCTL => regs2(&self.bar).dmatxctl.write_preserving(v),
            IxgbeRegs::EIAC => regs1(&self.bar).eiac.write_preserving(v),
            IxgbeRegs::EEC => regs3(&self.bar).eec.write_preserving(v),
            IxgbeRegs::DTXMXSZRQ => mac_regs(&self.bar).dtxmxszrq.write(v),
            IxgbeRegs::RTTDCS => regs2(&self.bar).rttdcs.write(v),
            IxgbeRegs::EICR => regs1(&self.bar).eicr.write(v),
            IxgbeRegs::EIMS => regs1(&self.bar).eims.write(v),
            IxgbeRegs::EIMC => regs1(&self.bar).eimc.write(v),
            IxgbeRegs::GPIE => regs1(&self.bar).gpie.write(v),
            // read-only statistics: a raw write was always ignored by hardware
            IxgbeRegs::STATUS | IxgbeRegs::LINKS
            | IxgbeRegs::GPRC | IxgbeRegs::GPTC | IxgbeRegs::GORCL
            | IxgbeRegs::GORCH | IxgbeRegs::GOTCL | IxgbeRegs::GOTCH => {}
            // stats outside the generated model: raw 32-bit path unchanged
            other => unsafe {
                ptr::write_volatile((self.bar.get_base() as u64 + other as u64) as *mut u32, v);
            },
        }
    }'''
assert OLD_SCALARS in s
s = s.replace(OLD_SCALARS, NEW_SCALARS)
n_subs += 1
open(p, "w").write(s)

# ---- ixgbe_regs.rs: typed region accessors + retargeted array layer ----
p = os.path.join(DRV, "src", "ixgbe_regs.rs")
s = open(p).read()
s = sub(s, r"use platform::PciBarAddr;",
        "use platform::PciBarAddr;\nuse crate::regs::*;\n\n"
        "// Typed access to the generated register model, overlaid on BAR0.\n"
        "// The raw pointer unsafety of the old base+offset math is concentrated\n"
        "// into these four casts.\n"
        "pub fn regs1(bar: &PciBarAddr) -> &'static mut IntelIxgbeRegisters1 {\n"
        "    unsafe { &mut *((bar.get_base() as usize) as *mut IntelIxgbeRegisters1) }\n"
        "}\n"
        "pub fn rx1_regs(bar: &PciBarAddr) -> &'static mut IntelIxgbeRxRegisters1 {\n"
        "    unsafe { &mut *((bar.get_base() as usize + 0x1000) as *mut IntelIxgbeRxRegisters1) }\n"
        "}\n"
        "pub fn regs2(bar: &PciBarAddr) -> &'static mut IntelIxgbeRegisters2 {\n"
        "    unsafe { &mut *((bar.get_base() as usize + 0x2000) as *mut IntelIxgbeRegisters2) }\n"
        "}\n"
        "pub fn tx_regs(bar: &PciBarAddr) -> &'static mut IntelIxgbeTxRegisters {\n"
        "    unsafe { &mut *((bar.get_base() as usize + 0x6000) as *mut IntelIxgbeTxRegisters) }\n"
        "}\n"
        "pub fn mac_regs(bar: &PciBarAddr) -> &'static mut IntelIxgbeMacRegisters {\n"
        "    unsafe { &mut *((bar.get_base() as usize + 0x8000) as *mut IntelIxgbeMacRegisters) }\n"
        "}\n"
        "pub fn regs3(bar: &PciBarAddr) -> &'static mut IntelIxgbeRegisters3 {\n"
        "    unsafe { &mut *((bar.get_base() as usize + 0xE000) as *mut IntelIxgbeRegisters3) }\n"
        "}")

OLD_DMA_RW = '''    #[inline(always)]
    pub fn read_reg_idx(&self, reg_enum: IxgbeDmaArrayRegs, idx: u64) -> u64 {
        let reg = self.get_array_reg(reg_enum);

        if idx >= reg.num_regs {
            return 0;
        }
        let ret = unsafe {
            ptr::read_volatile((self.bar.get_base() as u64 + reg.offset + reg.multiplier * idx) as *const u64) & 0xFFFF_FFFF as u64
        };
        ret
    }


    #[inline(always)]
    pub fn write_reg_idx(&self, reg_enum: IxgbeDmaArrayRegs, idx: u64, val: u64) {
        let reg = self.get_array_reg(reg_enum);

        if idx < reg.num_regs {
            unsafe {
                ptr::write_volatile((self.bar.get_base() as u64 + reg.offset + reg.multiplier * idx) as *mut u32, val as u32)
            }
        }

    }
}'''
NEW_DMA_RW = '''    #[inline(always)]
    pub fn read_reg_idx(&self, reg_enum: IxgbeDmaArrayRegs, idx: u64) -> u64 {
        let reg = self.get_array_reg(reg_enum);
        if idx >= reg.num_regs {
            return 0;
        }
        let i = idx as usize;
        u64::from(match reg_enum {
            IxgbeDmaArrayRegs::Rdbal => rx1_regs(&self.bar).rx_regs1[i].rdbal.read(),
            IxgbeDmaArrayRegs::Rdbah => rx1_regs(&self.bar).rx_regs1[i].rdbah.read(),
            // old ArrayRegister declared RDLEN with stride 0x60 (should be
            // 0x40): for idx > 0 the raw math read RXDCTL of that queue
            IxgbeDmaArrayRegs::Rdlen => rx1_regs(&self.bar).rx_regs1[i].rdlen.read(),
            IxgbeDmaArrayRegs::Rdh => rx1_regs(&self.bar).rx_regs1[i].rdh.read(),
            IxgbeDmaArrayRegs::Rdt => rx1_regs(&self.bar).rx_regs1[i].rdt.read(),
            IxgbeDmaArrayRegs::DcaRxctrl => rx1_regs(&self.bar).rx_regs1[i].dca_rxctrl.read(),
            // normalized from the 16-entry 82598-compat bank (0x2100) to the
            // documented primary bank inside the queue block
            IxgbeDmaArrayRegs::Srrctl => rx1_regs(&self.bar).rx_regs1[i].srrctl.read(),
            IxgbeDmaArrayRegs::Rxpbsize => regs2(&self.bar).rxpbsize[i].read(),
            IxgbeDmaArrayRegs::Rxdctl => rx1_regs(&self.bar).rx_regs1[i].rxdctl.read(),
            IxgbeDmaArrayRegs::Tdbal => tx_regs(&self.bar).tx_regs[i].tdbal.read(),
            IxgbeDmaArrayRegs::Tdbah => tx_regs(&self.bar).tx_regs[i].tdbah.read(),
            IxgbeDmaArrayRegs::Tdlen => tx_regs(&self.bar).tx_regs[i].tdlen.read(),
            IxgbeDmaArrayRegs::Tdh => tx_regs(&self.bar).tx_regs[i].tdh.read(),
            IxgbeDmaArrayRegs::Tdt => tx_regs(&self.bar).tx_regs[i].tdt.read(),
            IxgbeDmaArrayRegs::Txpbsize => mac_regs(&self.bar).txpbsize[i].read(),
            // normalized from the legacy 0x7200 bank to the documented
            // per-queue DCA_TXCTRL inside the tx queue block
            IxgbeDmaArrayRegs::DcaTxctrl => tx_regs(&self.bar).tx_regs[i].dca_txctrl.read(),
            IxgbeDmaArrayRegs::Txdctl => tx_regs(&self.bar).tx_regs[i].txdctl.read(),
            IxgbeDmaArrayRegs::Ivar => regs1(&self.bar).ivar[i].read(),
            IxgbeDmaArrayRegs::Eitr => regs1(&self.bar).eitr[i].read(),
            // TXPBTHRESH (0x4950) is outside the generated model: raw path,
            // now a correct 32-bit read
            IxgbeDmaArrayRegs::TxpbThresh => unsafe {
                ptr::read_volatile((self.bar.get_base() as u64 + reg.offset + reg.multiplier * idx) as *const u32)
            },
        })
    }

    #[inline(always)]
    pub fn write_reg_idx(&self, reg_enum: IxgbeDmaArrayRegs, idx: u64, val: u64) {
        let reg = self.get_array_reg(reg_enum);
        if idx >= reg.num_regs {
            return;
        }
        let i = idx as usize;
        let v = val as u32;
        match reg_enum {
            IxgbeDmaArrayRegs::Rdbal => rx1_regs(&self.bar).rx_regs1[i].rdbal.write(v),
            IxgbeDmaArrayRegs::Rdbah => rx1_regs(&self.bar).rx_regs1[i].rdbah.write(v),
            IxgbeDmaArrayRegs::Rdlen => rx1_regs(&self.bar).rx_regs1[i].rdlen.write(v),
            IxgbeDmaArrayRegs::Rdh => rx1_regs(&self.bar).rx_regs1[i].rdh.write(v),
            IxgbeDmaArrayRegs::Rdt => rx1_regs(&self.bar).rx_regs1[i].rdt.write(v),
            IxgbeDmaArrayRegs::DcaRxctrl => rx1_regs(&self.bar).rx_regs1[i].dca_rxctrl.write(v),
            IxgbeDmaArrayRegs::Srrctl => rx1_regs(&self.bar).rx_regs1[i].srrctl.write(v),
            IxgbeDmaArrayRegs::Rxpbsize => regs2(&self.bar).rxpbsize[i].write(v),
            IxgbeDmaArrayRegs::Rxdctl => rx1_regs(&self.bar).rx_regs1[i].rxdctl.write(v),
            IxgbeDmaArrayRegs::Tdbal => tx_regs(&self.bar).tx_regs[i].tdbal.write(v),
            IxgbeDmaArrayRegs::Tdbah => tx_regs(&self.bar).tx_regs[i].tdbah.write(v),
            IxgbeDmaArrayRegs::Tdlen => tx_regs(&self.bar).tx_regs[i].tdlen.write(v),
            // Gate: TDH is writable only while the queue is disabled;
            // force-the-action: minting the witness clears TXDCTL.ENABLE
            IxgbeDmaArrayRegs::Tdh => {
                let txq = &mut tx_regs(&self.bar).tx_regs[i];
                let witness = TxdctlEnableCleared::establish(&mut txq.txdctl);
                txq.tdh.write(v, &witness);
            }
            IxgbeDmaArrayRegs::Tdt => tx_regs(&self.bar).tx_regs[i].tdt.write(v),
            IxgbeDmaArrayRegs::Txpbsize => mac_regs(&self.bar).txpbsize[i].write(v),
            IxgbeDmaArrayRegs::DcaTxctrl => tx_regs(&self.bar).tx_regs[i].dca_txctrl.write(v),
            IxgbeDmaArrayRegs::Txdctl => tx_regs(&self.bar).tx_regs[i].txdctl.write(v),
            IxgbeDmaArrayRegs::Ivar => regs1(&self.bar).ivar[i].write(v),
            IxgbeDmaArrayRegs::Eitr => regs1(&self.bar).eitr[i].write(v),
            IxgbeDmaArrayRegs::TxpbThresh => unsafe {
                ptr::write_volatile((self.bar.get_base() as u64 + reg.offset + reg.multiplier * idx) as *mut u32, v)
            },
        }
    }
}'''
assert OLD_DMA_RW in s
s = s.replace(OLD_DMA_RW, NEW_DMA_RW)
n_subs += 1

OLD_ND_RW = '''    #[inline(always)]
    pub fn read_reg_idx(&self, reg_enum: IxgbeNoDmaArrayRegs, idx: u64) -> u64 {
        let reg = self.get_array_reg(reg_enum);

        if idx >= reg.num_regs {
            return 0;
        }
        let ret = unsafe {
            ptr::read_volatile((self.bar.get_base() as u64 + reg.offset + reg.multiplier * idx) as *const u64) & 0xFFFF_FFFF as u64
        };
        ret
    }


    #[inline(always)]
    pub fn write_reg_idx(&self, reg_enum: IxgbeNoDmaArrayRegs, idx: u64, val: u64) {
        let reg = self.get_array_reg(reg_enum);

        if idx < reg.num_regs {
            unsafe {
                ptr::write_volatile((self.bar.get_base() as u64 + reg.offset + reg.multiplier * idx) as *mut u32, val as u32)
            }
        }

    }
}'''
NEW_ND_RW = '''    #[inline(always)]
    pub fn read_reg_idx(&self, reg_enum: IxgbeNoDmaArrayRegs, idx: u64) -> u64 {
        let reg = self.get_array_reg(reg_enum);
        if idx >= reg.num_regs {
            return 0;
        }
        u64::from(match (reg_enum, idx) {
            // the generated model covers RAL/RAH entry 0 (the driver-visible
            // MAC address); other entries and QPTC/RXMPC keep the raw path,
            // now as correct 32-bit reads
            (IxgbeNoDmaArrayRegs::Ral, 0) => mac_regs(&self.bar).ral.read(),
            (IxgbeNoDmaArrayRegs::Rah, 0) => mac_regs(&self.bar).rah.read(),
            _ => unsafe {
                ptr::read_volatile((self.bar.get_base() as u64 + reg.offset + reg.multiplier * idx) as *const u32)
            },
        })
    }

    #[inline(always)]
    pub fn write_reg_idx(&self, reg_enum: IxgbeNoDmaArrayRegs, idx: u64, val: u64) {
        let reg = self.get_array_reg(reg_enum);
        if idx >= reg.num_regs {
            return;
        }
        match (reg_enum, idx) {
            (IxgbeNoDmaArrayRegs::Ral, 0) => mac_regs(&self.bar).ral.write(val as u32),
            (IxgbeNoDmaArrayRegs::Rah, 0) => mac_regs(&self.bar).rah.write(val as u32),
            _ => unsafe {
                ptr::write_volatile((self.bar.get_base() as u64 + reg.offset + reg.multiplier * idx) as *mut u32, val as u32)
            },
        }
    }
}'''
assert OLD_ND_RW in s
s = s.replace(OLD_ND_RW, NEW_ND_RW)
# the NoDma enum needs Copy for the match-after-get_array_reg pattern
s = sub(s, r"(pub enum IxgbeNoDmaArrayRegs \{)", "#[derive(Copy, Clone)]\n\\1")
n_subs += 1
open(p, "w").write(s)
print(f"port applied: {n_subs} block replacements")
