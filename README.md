# The Stellaluna Keyer

A CW keyer built around an Arduino Mega running the [K3NG keyer](https://github.com/k3ng/k3ng_cw_keyer)
firmware, with an ESP32 adapter that takes the keyer onto [VBand](https://hamradio.solutions/vband/) over WiFi.
Named after Stella (Stellaluna), a very good dog.

This repo is the project's home: the hardware (netlist, schematics, build photos, and later the KiCad boards) and
the map of how the pieces fit together. The firmware lives in its own repos.

## The pieces

| Part | Where | What |
|---|---|---|
| Keyer firmware | [W7YFR/k3ng_cw_keyer](https://github.com/W7YFR/k3ng_cw_keyer), branch `w7yfr` | Fork of K3NG's keyer: OLED, settings menu, the VBand link |
| Adapter firmware | [W7YFR/k3ng-vband-adapter](https://github.com/W7YFR/k3ng-vband-adapter) | ESP32 (Wemos D1 Mini32): WiFi, VBand, received audio, the link to the keyer |
| Hardware | this repo, [`hardware/`](hardware/) | Netlist, schematics, photos of the hand-wired v0 build |

The boards:
- **HAT**: shield on the Mega. Barrel jack and fuse, the ESP32 socket, the amp module and the link resistors. Every
  other jack (paddle, headphones, line out, speaker, straight key, radio key) is panel-mounted and plugs into a
  male JST header on the HAT: 3-pin for the paddle and headphones, 2-pin for the rest.
- **Front panel (FP)**: the three volume knobs, eight buttons, the LEDs and the OLED. Joins the HAT through J_FP.
- **Latch board (LB)**: the ESP32's soft power latch and button, and the WPM and Farnsworth pots. Joins the HAT
  through J_LB.

## Hardware docs

- [`hardware/netlist.md`](hardware/netlist.md): every part and net, both header pinouts, and the proposed changes.
  This is the source of truth; change it first.
- [`hardware/schematics.md`](hardware/schematics.md): the schematics, one sheet per circuit, as built and proposed.
  Viewable right on GitHub.
- [`hardware/schematics.html`](hardware/schematics.html): the same sheets with an As built / Proposed switch, plus the
  header pinouts and a parts list. Download it and open it in a browser.
- [`hardware/schematic-gen/`](hardware/schematic-gen/): the Python that draws the schematics page (see its README).
- [`hardware/photos/v0/`](hardware/photos/v0/): the hand-drawn stripboard layouts and photos of the v0 boards, plus
  the earlier breadboard design. The `*-aligned.jpg` pairs are each board's two sides drawn so the holes line up;
  [`hat-flip.gif`](hardware/photos/v0/hat-flip.gif) and
  [`latch-board-flip.gif`](hardware/photos/v0/latch-board-flip.gif) flip between them to show what connects
  through the board.

## Roadmap

Future work, bugs and features across all three repos: [ROADMAP.md](ROADMAP.md).

## Changelogs

- Hardware and docs: [CHANGELOG.md](CHANGELOG.md)
- Keyer fork: [CHANGELOG-W7YFR.md](https://github.com/W7YFR/k3ng_cw_keyer/blob/w7yfr/CHANGELOG-W7YFR.md)
- Adapter: [CHANGELOG.md](https://github.com/W7YFR/k3ng-vband-adapter/blob/main/CHANGELOG.md)

## Pin assignments

What each firmware expects on each pin. Almost nothing is wired pin to pin: the "Circuit" column names the
parts in between, and that sheet in [schematics.md](hardware/schematics.md) shows the full circuit. If a pin moves, change it here, in the
netlist, and in the firmware (`keyer_pin_settings.h` in the keyer, `include/pins.h` in the adapter).

**Mega**

| Pin | Firmware use | Circuit (schematics sheet) |
|---|---|---|
| D7 | VBand key line out | 10k / 22k divider to ESP32 GPIO22 (Mega ↔ ESP32 link) |
| D16 | link TX (Serial2) | 10k / 22k divider to ESP32 GPIO19 (Mega ↔ ESP32 link) |
| D17 | link RX (Serial2) | 10k series resistor from ESP32 GPIO18 (Mega ↔ ESP32 link) |
| D20 | OLED SDA | direct, via J_FP (LEDs and OLED) |
| D21 | OLED SCL | direct, via J_FP (LEDs and OLED) |
| D30 | paddle dit | paddle jack tip, 10nF to GND (Paddle and speed pots) |
| D32 | paddle dah | paddle jack ring, 10nF to GND (Paddle and speed pots) |
| D34 | straight key (not enabled yet) | J6 connector to the straight key jack, 10nF to GND (TX keying and straight key) |
| D44 | ESP32 power-on (proposed) | 10k into a transistor on the latch's gate (ESP32 power latch) |
| D46 | sidetone key out (proposed) | 10k / 22k divider to ESP32 GPIO21 (Audio) |
| D49 | radio keying (TX 1) | 2.2k into the keying transistor (TX keying and straight key); also the TX LED through 1k |
| D48 | spare LED (free to repurpose) | LED and 4.7k to GND (LEDs and OLED) |
| D50 | command mode LED | LED and 220Ω to GND (LEDs and OLED) |
| D52 | sidetone | main and line-out volume circuits (Audio) |
| A0 | Farnsworth pot | latch board pot wiper, 10nF to GND (Paddle and speed pots) |
| A1 | buttons | 10k / 1k resistor ladder, 8 buttons (Button ladder) |
| A2 | WPM pot | latch board pot wiper, 10nF to GND (Paddle and speed pots) |

**ESP32 (Wemos D1 Mini32)**

| Pin | Firmware use | Circuit (schematics sheet) |
|---|---|---|
| GPIO4 | power latch hold | 10k into the latch transistor T1 (ESP32 power latch) |
| GPIO15 | status LED | LED and 220Ω to GND (LEDs and OLED) |
| GPIO17 | latch / channel button | diode to the latch button (ESP32 power latch) |
| GPIO18 | link TX | 10k series resistor to Mega D17 (Mega ↔ ESP32 link) |
| GPIO19 | link RX | divider from Mega D16 (Mega ↔ ESP32 link) |
| GPIO21 | sidetone key in (proposed) | divider from Mega D46 (Audio) |
| GPIO22 | key in | divider from Mega D7 (Mega ↔ ESP32 link) |
| GPIO25 | received audio (DAC1) | volume pot, 3.3µF and 22k into the headphone circuit (Audio) |
| GPIO26 | own-keying sidetone (DAC2, proposed) | 1µF and 2.2k onto the Mega sidetone line (Audio) |


## Keeping the repos in sync

The three repos are independent; there are no submodules.
- **The link checks itself.** Both firmwares announce a link protocol version and show "Link Mismatch" if they
  disagree, so the two firmwares never have to be updated in lockstep. Bump the version only for a breaking change,
  in both repos at once.
- **Known-good sets.** When a combination is tested and working together, tag all three repos with the same name
  (for example `set-2026-10`) and add a row below. Checking out that tag in each repo gets you back to it.

| Set | Hardware | Keyer (`w7yfr`) | Adapter (`main`) | Link protocol | Notes |
|---|---|---|---|---|---|
| (untagged) 2026-10-07 | v0 hand-wired | `b37df8f` | `994b395` | 1 | settings menu, start modes, lobby, room counts |

## Getting set up

Clone this repo into an empty folder, then from it:

```sh
make setup     # clones the keyer fork and the adapter next to this repo
make doctor    # checks the tools and repos, and says how to fix anything missing
make help      # everything else: schematics, keyer and adapter builds
```

## Building and flashing

- Keyer: `make keyer-build` builds any checkout, worktree or branch (including ones cut from upstream `master`,
  which has no PlatformIO setup); see `tools/keyer-build/`. On the `w7yfr` checkout, `pio run -e w7yfr` also works.
  Flash with `pio run -e w7yfr -t upload` or the Arduino IDE.
- Adapter: `make adapter-build`; upload over USB (`pio run -e wemos_d1_mini32 -t upload`) or OTA once it's on WiFi.
  See the adapter's README.
- When both boards are on USB, pull JP1 (the ESP32 5V jumper) and keep the barrel supply off.

## License

MIT, see [LICENSE](LICENSE).
