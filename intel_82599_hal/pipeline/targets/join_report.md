# Driver <-> Table 8-2 join report

- Table 8-2 rows parsed: **406** (380 unique abbreviation bases)
- regs.rs registers: **75** (driver-needed: **63**)
- Auto-joined by name: **75** / 75
- Unmatched (need name_map.json entries — logged friction): **0**


## Auto-join (field -> datasheet abbrev @ offset)
| field | abbrev | offset_raw | rw |
|---|---|---|---|
| autoc | AUTOC | 0x042A0 | RW |
| autoc2 | AUTOC2 | 0x042A8 | RW |
| ctrl | CTRL | 0x00000 / 0x00004 | RW |
| ctrl_ext | CTRL_EXT | 0x00018 | RW |
| daqf | DAQF[n] | 0x0E200+4*n, n=0...127 | RW |
| dca_ctrl | DCA_CTRL | 0x11074 | RW |
| dca_id | DCA_ID | 0x11070 | RO |
| dca_rxctrl | DCA_RXCTRL[n] | 0x0100C+0x40*n, n=0...63 and 0x0D00C+0x40*(n-64), n=64...127 / 0x02200+4*n, [n=0...15] | RW |
| dca_txctrl | DCA_TXCTRL[n] | 0x0600C+0x40*n, n=0...127 | RW |
| dmatxctl | DMATXCTL | 0x04A80 | RW |
| dtxmxszrq | DTXMXSZRQ | 0x08100 | RW |
| dtxtcpflgh | DTXTCPFLGH | 0x04A8C | RW |
| dtxtcpflgl | DTXTCPFLGL | 0x04A88 | RW |
| eec | EEC | 0x10010 | RW |
| eerd | EERD | 0x10014 | RW |
| eiac | EIAC | 0x00810 | RW |
| eiam | EIAM | 0x00890 | RW |
| eicr | EICR | 0x00800 | RW1C |
| eics | EICS | 0x00808 | WO |
| eimc | EIMC | 0x00888 | WO |
| eims | EIMS | 0x00880 | RWS |
| eitr | EITR[n] | 0x00820+4*n, n=0...23 and 0x012300+4*(n-24), n=24...128 | RW |
| etqf | ETQF[n] | 0x05128+4*n, n=0...7 | RW |
| etqs | ETQS[n] | 0x0EC00+4*n, n=0...7 | RW |
| fccfg | FCCFG | 0x03D00 | RW |
| fcrth | FCRTH[n] | 0x03260+4*n, n=0...7 | RW |
| fcrtl | FCRTL[n] | 0x03220+4*n, n=0...7 | RW |
| fcrtv | FCRTV | 0x032A0 | RW |
| fctrl | FCTRL | 0x05080 | RW |
| fcttv | FCTTVn | 0x03200+4*n, n=0...3 | RW |
| ftqf | FTQF[n] | 0x0E600+4*n, n=0...127 | RW |
| gorch | GORCH | 0x0408C | RC |
| gorcl | GORCL | 0x04088 | RC |
| gotch | GOTCH | 0x04094 | RC |
| gotcl | GOTCL | 0x04090 | RC |
| gpie | GPIE | 0x00898 | RW |
| gprc | GPRC | 0x04074 | RC |
| gptc | GPTC | 0x04080 | RO |
| hlreg0 | HLREG0 | 0x04240 | RW |
| i2cctl | I2CCTL | 0x00028 | RW |
| ivar | IVAR[n] | 0x00900+4*n, n=0...63 | RW |
| l34timir | L34TIMIR[n] | 0x0E800+4*n, n=0...127 | RW |
| links | LINKS | 0x042A4 | RO |
| links2 | LINKS2 | 0x04324 | RO |
| mrqc | MRQC | 0x0EC80 / 0x05818 | RW |
| rah | RAH[n] | 0x0A204+8*n, n=0...127 | RW |
| ral | RAL[n] | 0x0A200+8*n, n=0...127 | RW |
| rdbah | RDBAH[n] | 0x01004+0x40*n, n=0...63 | RW |
| rdbal | RDBAL[n] | 0x01000+0x40*n, n=0...63 | RW |
| rdh | RDH[n] | 0x01010+0x40*n, n=0...63 | RO |
| rdlen | RDLEN[n] | 0x01008+0x40*n, n=0...63 | RW |
| rdrxctl | RDRXCTL | 0x02F00 | RW |
| rdt | RDT[n] | 0x01018+0x40*n, n=0...63 | RW |
| reta | RETA[n] | 0x0EB00+4*n, n=0...31 | RW |
| rssrk | RSSRK[n] | 0x0EB80+4*n, n=0...9 | RW |
| rttdcs | RTTDCS | 0x04900 | RW |
| rxcsum | RXCSUM | 0x05000 | RW |
| rxctrl | RXCTRL | 0x03000 | RW |
| rxdctl | RXDCTL[n] | 0x01028+0x40*n, n=0...63 | RW |
| rxpbsize | RXPBSIZE[n] | 0x03C00+4*n, n=0...7 | RW |
| saqf | SAQF[n] | 0x0E000+4*n, n=0...127 | RW |
| sdpqf | SDPQF[n] | 0x0E400+4*n, n=0...127 | RW |
| srrctl | SRRCTL[n] | 0x01014+0x40*n, n=0...63 | RW |
| status | STATUS | 0x00008 | RO |
| sw_fw_sync | SW_FW_SYNC | 0x10160 | RW |
| swsm | SWSM | 0x10140 | RW |
| tdbah | TDBAH[n] | 0x06004+0x40*n, n=0...127 | RW |
| tdbal | TDBAL[n] | 0x06000+0x40*n, n=0...127 | RW |
| tdh | TDH[n] | 0x06010+0x40*n, n=0...127 | RO |
| tdlen | TDLEN[n] | 0x06008+0x40*n, n=0...127 | RW |
| tdt | TDT[n] | 0x06018+0x40*n, n=0...127 | RW |
| tdwbah | TDWBAH[n] | 0x0603C+0x40*n, n=0...127 | RW |
| tdwbal | TDWBAL[n] | 0x06038+0x40*n, n=0...127 | RW |
| txdctl | TXDCTL[n] | 0x06028+0x40*n, n=0...127 | RW |
| txpbsize | TXPBSIZE[n] | 0x0CC00+0x4*n, n=0...7 | RW |
