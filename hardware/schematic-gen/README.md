# Schematic generator

Draws the Stellaluna schematics from hand-placed coordinates: `../schematics.html` (the interactive page), and
`../schematics.md` with one SVG per sheet in `../schematics/` (for viewing on GitHub). All of them are generated;
don't edit them by hand. The source of
truth for what connects to what is `../netlist.md`: change the netlist first, then the drawing here.

## Files

- `sym.py`: a tiny SVG schematic library (`standalone()` gives a self-contained SVG with its own light and dark
  colors, for markdown). A `Sheet` collects parts placed at explicit pixel coordinates (wires,
  resistors, caps, diodes/LEDs, pots, buttons, switches, fuse, NPN, P-MOSFET, boxes for modules and jacks, ports,
  grounds, rails, notes). Colors come from CSS classes: `w` as built, `n` new/proposed, `x` to remove
  (set `sheet.cls` before drawing, then back to `'w'`).
- `circuits.py`: one function per sheet (`power`, `latch`, `link`, `audio`, `inputs`, `buttons`, `leds`, `txkey`);
  those with a `proposed` flag draw both versions. `ALL` maps preview names to them.
- `build_page.py`: assembles the page: sheet titles and descriptions (`SECTIONS`), header pinouts (`J_FP`,
  `J_LB`), the parts list (`BOM`) and the proposed-changes list (`CHANGES`), into `page_template.html`.
- `page_template.html`: page layout, theme tokens (light/dark) and the As built / Proposed switch.

## Use

Needs only Python 3 (no packages) for the page. Previews need `rsvg-convert` (Homebrew `librsvg`).

```sh
python3 build_page.py                       # writes ../schematics.html, ../schematics.md, ../schematics/*.svg
python3 circuits.py latch-p                 # writes out/latch-p.svg + .png previews (out/ is git-ignored)
```

Value codes are the builder's: R1 10k, R2 1k, R3 4.7k, R4 220, R5 2.2k, R6 220k, R7 47k, R8 1M, R9 22k;
C1 100nF, C2 10nF, C3 1000uF, C4 3.3uF, C5 1uF, C6 470uF. A code appears wherever that value is used.

## Workflow

1. Change `../netlist.md` first: it's the record of what's on the boards.
2. Update the drawing in `circuits.py` (and the tables in `build_page.py` if parts, pins or changes moved).
3. Preview the sheets you touched (`python3 circuits.py <name>`) and look for overlapping labels and wires.
4. Rebuild with `python3 build_page.py`, open `../schematics.html` in a browser and check `../schematics.md`.
5. Commit the generated files together with the source changes.
