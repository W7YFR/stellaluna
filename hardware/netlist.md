# Stellaluna netlist (v0, as built)

**Status: complete for the v0 build (checked 2026-10-10).** Built from the hand-drawn layouts in `photos/v0/`, the
builder's descriptions, the K3NG pin settings and the adapter firmware's `pins.h`. The schematics
(`schematics.md`, `schematics.html`) are drawn from this file, and the KiCad project will start from it.

Boards:
- **HAT**: shield on the Arduino Mega 2560 (barrel jack, fuse, ESP32 socket, amp, jacks, link resistors).
- **FP** (front panel daughter board): main / line-out / ESP32 volume pots, 8 buttons with the resistor ladder,
  LEDs. Joins the HAT through the top header (J_FP).
- **LB** (latch board): soft power latch for the ESP32, WPM and Farnsworth pots. Joins the HAT through the bottom
  header (J_LB).

Value codes the drawings use as designators (confirmed 2026-10-07; a code can appear many times):
- Resistors: R1 = 10k, R2 = 1k, R3 = 4.7k, R4 = 220, R5 = 2.2k, R6 = 220k, R7 = 47k, R8 = 1M, R9 = 22k.
- Caps: C1 = 100 nF ceramic, C2 = 10 nF ceramic, C3 = 1000 uF elec, C4 = 3.3 uF elec, C5 = 1 uF ceramic,
  C6 = 470 uF elec.
- Pots: P1 = 10k linear (speed pots), P2 = 10k log (all three volume pots; they were 500k and 250k before
  2026-10-08).
- T1 = 2N2222A, M1 = IRF5305, D1 = 1N4148, fuse 2 A.
- From the breadboard drawing (`photos/v0/breadboard-drawing.jpg`, the earlier 12V + LM2596 design): paddle caps = C2 10nF
  each line to GND; CMD LED = D50 -> LED -> R4 220 -> GND; spare LED = D48 -> LED -> R3 4.7k -> GND; TX keying =
  D49 -> R5 2.2k -> NPN base; LM386 supply = C5 1uF + C1 100nF; C3 1000uF across the 5V rail; C6 470uF on the
  old buck output; R6 220k / R7 47k = the old divider tap from the TX line to the ESP32 (removed in the link
  work). The breadboard's decoder input (C1 / C2) was never built on this board. Confirmed 2026-10-10: no C3 anywhere
  now (it was on the OLED's 5V, removed); R6 / R7 unused; C6 470uF + C1 100nF are back across the ESP32's 5V/GND
  (added for the reconnect issue).

## Parts

Every jack except the barrel jack is panel-mounted and reaches the HAT through a male JST header: 3-pin for the
paddle and headphones, 2-pin for everything else.

| Ref | Part | Board | Notes |
|---|---|---|---|
| U1 | Arduino Mega 2560 | under HAT | |
| U2 | Wemos D1 Mini32 (ESP32) | HAT, socketed | |
| U3 | LM386 module (amazon B07P38H4P8), R0 removed = 20x gain | HAT | the 4-pin block, with C5 1uF + C1 100nF on its supply |
| U4 | SSD1306 OLED 128x64 I2C, 4-pin | FP, next to the buttons | |
| J1 | 5V DC barrel jack (on the HAT itself) | HAT | |
| F1 | fuse 2 A | HAT | |
| SW_PWR | power switch, after the fuse (via the "To switch" connector) | off board | **not wired yet** |
| JP1 | ESP 5V jumper, 2-pin | HAT | breaks +5V_LATCHED; pulled when both boards are on USB |
| J2 | paddle, 3-pin JST (tip, ring, sleeve) to the panel TRS jack | HAT | |
| J3 | headphones, 3-pin JST (T/R/R' tied at the jack, T' switched, sleeve) to the panel switched stereo jack | HAT ("AMP") | plugging in cuts the LM386 input |
| J4 | line out, 2-pin JST (tip, sleeve) to the panel jack | HAT ("LO") | |
| J5 | speaker, 2-pin JST | HAT ("SPKR") | |
| J6 | straight key, 2-pin JST (tip, sleeve) to the panel TRS jack | HAT | not wired yet |
| J7 | radio key, 2-pin JST (tip, sleeve) to the panel jack | HAT | not wired yet |
| J_FP | header to the front panel | HAT/FP | pin list below |
| J_LB | header to the latch board | HAT/LB | pin list below |
| VR1 | main volume, 500k log | FP | |
| VR2 | line out volume, 500k log | FP | |
| VR3 | ESP32 (received) volume, 250k | FP | |
| VR4 | WPM speed pot, 10k linear | LB | |
| VR5 | Farnsworth pot, 10k linear | LB | |
| SW1..SW8 | pushbuttons (command, 6 memories, 1 extra) | FP | analog ladder on A1 |
| SW9 | ESP32 power/channel button | LB | |
| M1 | IRF5305 P-MOSFET | LB | |
| T1 | 2N2222A | LB | latch hold |
| T2 | 2N2222A | HAT | TX keying (not wired yet) |
| D1, D2 | 1N4148 | LB | D1 gate -> SW_NODE, D2 GPIO17 -> SW_NODE (confirmed; based on the common Arduino soft-latch design, IRF4905 swapped for IRF5305) |
| LED_TX | D49 -> R1 1k -> LED -> GND (changed 2026-10-07) | FP | |
| LED_CMD | D50 -> LED -> R4 220 -> GND (R4 on the HAT) | FP | |
| LED_ESP | GPIO15 -> LED -> R4 220 -> GND | FP | |
| LED_SPARE | D48 -> LED -> R3 4.7k -> GND | FP | was the decoder LED; free to repurpose |

## Power

| Net | Connects |
|---|---|
| **VIN_RAW** | J1 + -> F1 |
| **VIN_FUSED** | F1 -> "To switch" connector pin 1 (SW_PWR not wired yet; the connector is jumpered for now) |
| **+5V** | switch connector pin 2, Mega 5V pin (directly, not through VIN), U3 VCC, U4 VCC, J_FP 24, J_LB 3 (M1 source), J_LB 8 / 9 (pot ends) |
| **+5V_LATCHED** | LB M1 drain -> J_LB "Latched 5V" -> JP1 -> U2 5V pin |
| **GND** | J1 -, Mega GND, U2 GND, U3 GND, U4 GND, J2 S, J3 S, J4 S, J5 -, J_FP GND, J_LB GND, all caps' - |

Note (by practice the barrel is never on while the Mega is on USB; a power-path stage is planned for KiCad v1): with the Mega's USB plugged in while +5V is powered, the computer's USB 5V and +5V are tied (the Mega only
isolates USB from VIN, not from its 5V pin).

## Soft power latch (LB) -- as in the adapter README, values per the LB drawing

| Net | Connects |
|---|---|
| +5V | M1 source, R8 1M (gate pull-up) |
| GATE | M1 gate, T1 collector, D1 anode, R8 1M to M1 source |
| SW_NODE | D1 cathode, D2 cathode, SW9 one side |
| SW9 other side | GND |
| LATCH | U2 GPIO4 -> J_LB "latch" -> R1 10k -> T1 base |
| T1 base | R1 10k from LATCH, R8 1M to GND |
| T1 emitter | GND |
| ESP_BTN | U2 GPIO17 -> J_LB "ESP BTN" -> D2 anode |
| +5V_LATCHED | M1 drain |

## Mega <-> ESP32 link (HAT) -- matches the adapter README

| Net | Connects |
|---|---|
| D16 (TX2) | 10k (R1) -> LINK_RX |
| LINK_RX | U2 GPIO19, R9 22k to GND (5V x 22/32 = 3.44V high; ESP32 max 3.6V) |
| D17 (RX2) | 10k (R1) -> U2 GPIO18 |
| D7 (VBand key) | R1 10k -> KEY_ESP |
| KEY_ESP | U2 GPIO22, R9 22k to GND |

## Speed pots (LB pots, caps on the HAT)

| Net | Connects |
|---|---|
| WPM | VR4 wiper -> J_LB 14 -> Mega A2, C2 10nF to GND at the Mega pin (HAT) |
| FARNS | VR5 wiper -> J_LB 13 -> Mega A0, C2 10nF to GND at the Mega pin (HAT) |
| (pot ends) | J_LB 9 / 8 +5V, other ends GND |

## Paddle (HAT)

| Net | Connects |
|---|---|
| DIT | J2 T -> Mega D30, C2 10nF to GND (tip = dit, confirmed) |
| DAH | J2 R -> Mega D32, C2 10nF to GND |
| (J2 S) | GND |


## TX keying output (HAT; wired, not yet connected)

| Net | Connects |
|---|---|
| TX1 | Mega D49 -> R5 2.2k -> T2 (2N2222A) base; also LED_TX (D49 -> R1 1k -> LED -> GND) |
| T2 emitter | GND |
| KEY_OUT | T2 collector -> J7 tip |
| (J7 sleeve) | GND |

## Straight key input (not wired yet)

| Net | Connects |
|---|---|
| STRAIGHT | J6 tip -> Mega D34, C2 10nF to GND |
| (J6 sleeve) | GND |

Firmware: not enabled yet. When the jack is wired, turn on FEATURE_STRAIGHT_KEY with pin_straight_key = 34 (its
default, 52, is the sidetone here). Until then the build uses FEATURE_STRAIGHT_KEY_PADDLE (the dit paddle in
straight mode).

## OLED (HAT)

| Net | Connects |
|---|---|
| SDA | Mega D20 -> J_FP SDA -> U4 SDA (OLED on the FP) |
| SCL | Mega D21 -> J_FP SCL -> U4 SCL |

## Buttons (FP) -- K3NG analog ladder (analog_buttons_r1 = 10k, analog_buttons_r2 = 1k)

| Net | Connects |
|---|---|
| BTN (A1) | Mega A1 -> J_FP "Button array" -> ladder node 0, R1 10k to +5V (on the FP, fed from J_FP 24) |
| ladder | node 0 -- SW1 -- GND; node 0 -R2- node 1 -- SW2 -- GND; ... node 7 -- SW8 -- GND |

Topology confirmed by the breadboard drawing (A1 -- R1 10k -- +5V; buttons from each ladder node to GND, R2 1k
between nodes). Confirmed: 8 buttons, 7 x R2, the button directly on A1 is the command button (K3NG order:
command, memories 1-6, extra).

## Audio (HAT, pots on the FP)

| Net | Connects |
|---|---|
| ST_MEGA | Mega D52 -> J_FP 2 -> VR1 leg B; also R3 4.7k (line-out branch, on the HAT) |
| VR1 (main, 10k log) | leg B = ST_MEGA, leg A = GND, wiper -> J_FP 4 -> C4 3.3uF (+ toward VR1) -> R3 4.7k -> HP_NODE |
| LINE branch | ST_MEGA -> R3 4.7k -> C4 3.3uF -> J_FP 13 -> VR2 leg B; VR2 leg A = GND |
| VR2 (line out, 10k log) | wiper -> J_FP 12 -> J4 tip; J4 sleeve = GND |
| ST_ESP | U2 GPIO25 (DAC1) -> J_FP 20 -> VR3 leg B; VR3 leg A = GND |
| VR3 (received, 10k log) | wiper -> J_FP 21 -> C4 3.3uF -> R9 22k -> HP_NODE |
| HP_NODE | J3 "T, R, R'" pin (tied together at the jack), the main-branch R3, the ESP-branch R9 |
| AMP_IN | J3 T' pin (the jack's switched contact: carries HP_NODE only with no plug in) -> U3 IN |
| (J3 sleeve) | GND |
| AMP_OUT | U3 OUT+ / OUT- (the module has its own output cap) -> J5 |

All three volume pots were rewired as dividers on 2026-10-08 (signal into leg B, output from the wiper) and
changed from 500k/250k to 10k log. Before that, D52 and GPIO25 drove the wipers directly, which shorted them toward
GND at low volume and made the main knob change the line-out level too.

## Audio -- proposed

1. ESP32 own-keying sidetone: U2 GPIO26 (DAC2) -> C5 1uF -> R5 2.2k -> ST_MEGA (so VR1 and the line out carry it
   too). No resistor on D52. Firmware tri-states whichever source isn't selected (st.src = Mega / Adapter / Auto).
   R5 also limits the current into GPIO26 when the ESP32 is off (~1 mA).
   Sidetone key line (chosen 2026-10-10): Mega D46 -> R1 10k -> ST_KEY; ST_KEY -> U2 GPIO21 (silkscreen D2), R9 22k
   to GND. The keyer drives D46 high while its sidetone sounds (radio keying, VBand keying and command-mode beeps);
   D7 keeps meaning "key VBand".
2. Received VBand audio (GPIO25 -> VR3) stays on the headphones and speaker only: the line out carries only your
   own sending, which is what a keying trainer on the computer wants.
3. Amp drives headphones (independent of 1): HP_NODE -> U3 IN directly; U3 OUT+ -> J3 "T, R" pin (tip and ring
   tied at the jack); J3 T' (switched contact) -> J5 speaker +; J5 speaker - -> U3 OUT-; J3 sleeve -> GND. The
   headphones then get the amplified mix, so VBand audio is as loud there as on the speaker (today R9 22k into the
   ~32 ohm headphones leaves it about 7x quieter than the Mega sidetone). No new parts; J3's three pins become
   amp out, T' and sleeve. No series resistor between the amp and J3: it would also choke the speaker.

## Power -- proposed

- v0: no change (one +5V rail; rule: barrel off while on USB). The rail split proposed earlier was dropped
  (it cut the amp off on USB and still didn't protect the computer).
- KiCad v1: an ideal-diode / power-path stage on the barrel input (P-MOSFET or ideal-diode IC), so external
  power and the Mega's USB can never feed each other, with no diode drop.
- C6 470uF + C1 100nF at U2 5V/GND (on +5V_LATCHED). **Done 2026-10-10.**
- Pots: VR1/VR2/VR3 all 10k log (A10K), all wired as dividers. **Done 2026-10-08.**

## Part of the build, not wired yet

Treated as built in the schematics.
- SW_PWR power switch (into the "To switch" connector; jumpered for now).
- TX keying and the straight key: see the sections above.

## Proposed

- Mega D44 -> R1 10k -> T3 base (R8 1M base to GND), collector to GATE, emitter to GND (keyer powers the ESP32 on).

## Header pinouts (viewed from the front / button side, counting from the left)

J_FP, front panel, 24 pins (unlisted pins are unused):

| Pin | Signal |
|---|---|
| 1 | GND |
| 2 | Mega D52 sidetone (was straight to the main pot wiper; now to its leg) |
| 3 | Mega D50, command mode LED |
| 4 | main pot out -> (on the HAT) C4 3.3uF -> R3 4.7k -> HP_NODE |
| 7 | ESP32 LED (GPIO15) |
| 11 | spare LED (D48; free to repurpose) |
| 12 | line out -> tip |
| 13 | sidetone in: D52 -> (on the HAT) R3 4.7k -> C4 3.3uF -> line out pot leg |
| 14 | TX LED (D49) |
| 18 | button array (A1) |
| 20 | ESP32 sidetone (GPIO25; was straight to the ESP pot wiper; now to its leg) |
| 21 | ESP pot out -> (on the HAT) C4 3.3uF -> R9 22k -> HP_NODE |
| 22 | OLED SCL |
| 23 | OLED SDA |
| 24 | +5V: OLED VCC and the button ladder R1 10k pull-up |

J_LB, latch board, 16 pins (unlisted pins are unused):

| Pin | Signal |
|---|---|
| 2 | +5V_LATCHED out to the ESP32 (via JP1) |
| 3 | +5V in -> M1 source (pin 3); R8 1M from gate (pin 1) to source (confirmed) |
| 4 | LATCH (ESP32 GPIO4) |
| 8 | +5V in -> Farnsworth pot leg |
| 9 | +5V in -> WPM pot leg |
| 13 | Farnsworth pot wiper -> Mega A0 |
| 14 | WPM pot wiper -> Mega A2 |
| 15 | ESP BTN (GPIO17) |
| 16 | GND |
