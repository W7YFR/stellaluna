# Changelog

Hardware and docs for the Stellaluna Keyer. Firmware has its own changelogs:
[keyer](https://github.com/W7YFR/k3ng_cw_keyer/blob/w7yfr/CHANGELOG-W7YFR.md) and
[adapter](https://github.com/W7YFR/k3ng-vband-adapter/blob/main/CHANGELOG.md). Which firmware versions were tested
together with which hardware is in the README's known-good sets table.

## Unreleased

Planned work is in [ROADMAP.md](ROADMAP.md).

## 2026-10-10: repo created

### Added
- Netlist of the v0 hand-wired build (HAT, front panel, latch board), checked against the boards.
- Schematics: an HTML page with a toggle for each proposed change, a markdown version with one SVG per sheet, and
  the Python generator that draws them.
- Build photos and hand-drawn layouts (metadata stripped), with flip GIFs of each board's two sides.
- Planned and drawn as part of the build (not wired yet): TX keying output (J7), straight key on D34 (J6), power
  switch.

### Changed
- The decoder LED (D48) is kept as a spare indicator.

### Hardware
- 470µF + 100nF added across the ESP32's 5V and GND, for the reconnects seen on latch power.

## 2026-10-08

### Changed
- All three volume pots changed from 500k / 250k to 10k log and rewired as dividers (signal into an outer leg,
  output from the wiper). Before, D52 and GPIO25 drove the wipers, which shorted them toward ground at low volume and
  made the main knob change the line-out level.

## 2026-10-07

### Changed
- TX LED moved off the radio key line: now D49 -> 1k -> LED -> GND. It was pulled up to 5V on the transistor's
  collector, which fed current into the radio's key input and glowed with the radio off.

## v0: hand-wired build (through 2026-10-03)

### Added
- HAT on the Mega with the ESP32 socket, amp module, link dividers (10k / 22k) and JST connectors to the panel jacks.
- Front panel: three volume knobs, eight buttons on a resistor ladder, LEDs, OLED.
- Latch board: the ESP32's soft power latch (IRF5305 and 2N2222A) with its button, and the WPM and Farnsworth pots.
