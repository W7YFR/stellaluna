# Working on the Stellaluna Keyer

Notes for AI agents and contributors. Read README.md for what the project is; this file is how to work in it.

## Layout

Independent git repos (no submodules), checked out side by side in one workspace folder (`make setup` clones the
others next to this one):

| Repo | Folder | Branch | What |
|---|---|---|---|
| `W7YFR/stellaluna` | `stellaluna/` | `main` | Hardware docs, schematics, roadmap, tools; the project hub |
| `W7YFR/k3ng_cw_keyer` | `k3ng_cw_keyer/` | `w7yfr` | Keyer firmware, a fork of K3NG (`upstream` remote = k3ng) |
| `W7YFR/k3ng-vband-adapter` | `k3ng-vband-adapter/` | `main` | ESP32 VBand adapter firmware |
| `W7YFR/vband` (private) | `vband/` | `main` | Saved copies of the VBand web client and network captures, for the protocol |

Work from the workspace folder so all of them are in reach. `make doctor` checks the workspace and the tools.

## Make targets (run in `stellaluna/`)

| Target | What |
|---|---|
| `make setup` | Clone the other repos next to this one, add the K3NG `upstream` remote, fetch the adapter's submodule |
| `make doctor` | Check tools (git, python3, PlatformIO, rsvg-convert, exiftool), repos, branches, SSH; says how to fix gaps |
| `make schematics` | Regenerate the schematics from `hardware/schematic-gen/` |
| `make keyer-build` | Build the keyer: `KEYER=<checkout or worktree>`, `PRESET=<name>`, `ARGS='-D FEATURE_X'` |
| `make keyer-matrix` | Build every preset in `tools/keyer-build/presets/matrix.txt` |
| `make adapter-build` | Build the adapter (USB environment) |

None of them upload anything.

## Ground rules

- **Never flash or upload firmware**, over USB or OTA. Build only, then stop and ask the person to flash and test on
  the hardware. Don't open or write to serial ports or USB devices you weren't pointed at.
- **Don't commit, merge, amend or push unless asked.** Show the change first.
- Commits use the noreply address `331321620+W7YFR@users.noreply.github.com` (set per repo). Never put a personal
  email in commits or files.
- Nothing private in these public repos: no local paths, passwords, WiFi details or hostnames. The adapter's OTA
  password and hostname live in its git-ignored `.env`.
- Photos and images: strip all metadata (`exiftool -all= -overwrite_original`) before adding them, and check with
  `exiftool` afterwards. No PSD files.

## Hardware docs (this repo)

- `hardware/netlist.md` is the source of truth for what's on the boards. Change it first, then the drawings.
- The schematics are generated: `hardware/schematics.html`, `hardware/schematics.md` and `hardware/schematics/*.svg`
  all come from `hardware/schematic-gen/`. Never edit them by hand. Workflow and file roles are in
  `hardware/schematic-gen/README.md`. In short:
  1. Edit `circuits.py` (one function per sheet; proposals are keys in `SHEETS`, drawn in pink with `s.cls = 'n'`).
  2. Preview what you touched: `python3 circuits.py <variant>` writes `out/<variant>.png` (needs `rsvg-convert`).
     Look at it: check for overlapping labels and wires.
  3. Rebuild everything: `make schematics`. Commit the generated files with the source change.
- Designators use value codes, not unique numbers: R1 = 10k, R2 = 1k, R3 = 4.7k, R4 = 220, R5 = 2.2k, R6 = 220k,
  R7 = 47k, R8 = 1M, R9 = 22k; C1 = 100nF, C2 = 10nF, C3 = 1000µF, C4 = 3.3µF, C5 = 1µF, C6 = 470µF. Parts with their
  own identity get numbers: U1-U4, J1-J7, VR1-VR5, SW1-SW9, T1-T3, M1, D1-D2.
- Header pins (J_FP 24 pins, J_LB 16 pins) are numbered from the left, seen from the front (button side).
- Every panel jack reaches the HAT through a male JST header: 3-pin for the paddle and headphones, 2-pin for the
  rest. The barrel jack is on the HAT.
- "Proposed" means a change not yet decided or built. Parts that are designed but just not wired yet (TX keying,
  straight key, power switch) count as built.

## Keeping the three repos consistent

- **Pins:** a pin change touches the netlist, the README's pin assignments, and the firmware (`keyer_pin_settings.h`
  in the keyer, `include/pins.h` in the adapter).
- **Link protocol:** both firmwares send `HI,<version>` and warn on a mismatch. Bump `VBAND_LINK_PROTOCOL_VERSION`
  (keyer) and `MEGA_LINK_PROTOCOL_VERSION` (adapter) together, and only for breaking changes. New frame types are
  fine without a bump: both sides ignore types they don't know.
- **Changelogs:** each repo keeps its own (`CHANGELOG.md` here and in the adapter, `CHANGELOG-W7YFR.md` in the
  keyer). Keyer entries name the branch the change lives on. When a roadmap item is done, move it into the right
  changelog and delete it from `ROADMAP.md`.
- **Known-good sets:** when a combination is tested together, tag all three repos with the same name
  (`set-YYYY-MM`) and add a row to the README's table.

## Keyer fork workflow

- Fixes and features go on their own branch (`fix/...`, `feature/...`) cut from upstream `master`, or stacked on a
  branch they need. Keep them free of this build's configuration so others can merge them alone.
- New behavior goes behind a `FEATURE_` / `OPTION_` define. Settings in the settings menu appear only when the
  build has the feature or pin they need.
- This build's own configuration (pins, features on or off) is committed directly on `w7yfr` as
  `chore: ... for w7yfr build`.
- **New options go everywhere.** Every new `FEATURE_` / `OPTION_` define, setting or pin must be added (commented
  out or with a safe default) to every hardware profile's files, not just the generic ones:
  `keyer_features_and_options_*.h`, `keyer_settings_*.h` and `keyer_pin_settings_*.h` for each board, including
  `*_test_everything.h` (K3NG's compile-everything profile). Otherwise other people's builds break. The matrix build
  (below) catches what's missing.
- **The live checkout workflow.** Do the work in a worktree on the branch. Copy the same change, uncommitted, into
  the `w7yfr` checkout so the person can see the diff, build and flash it. Commit only after they've tested and
  approved; then commit on the branch, restore the `w7yfr` copy, merge with `--no-ff`, and check the merged files
  match what was tested.
- **Builds.** Feature branches cut from `master` have no PlatformIO setup, so use `tools/keyer-build/` (or the make
  targets): it builds any checkout or worktree with a preset (`--list` shows them; `w7yfr-features` turns this
  build's features on over any branch; `-D` / `-U` / `--set` add more). The `w7yfr` checkout also builds directly with
  `pio run -e w7yfr`.
- **Build cadence: favor progress.** While a change is in progress, build only when it's worth checking, and only
  the one configuration that matters (`as-is` on the `w7yfr` copy, or `w7yfr-features` on the branch). Don't run
  the matrix after each step. Run `make keyer-matrix` once, when the feature is believed done and before committing.
  It also builds each preset on `master` (cached per commit) and marks failures `master` already has as `old`; only
  `FAIL` lines are new problems. Some other boards' profiles fail on upstream `master` under PlatformIO (functions
  its prototype scanner misses), so `old` is expected there. The person flashes and tests quickly and will report
  problems.
- RAM is tight (about 51.5% used, 3.9 KB free): check the RAM figure in the build summary, and put large tables and
  strings in `PROGMEM`.
- Arduino's generated prototypes can mention types declared inside `#ifdef`s: define such structs unconditionally.

## Adapter workflow

- Branch from `main` for features and merge back.
- Build: `make adapter-build` or `pio run -e wemos_d1_mini32` (OTA upload environment `wemos_d1_mini32_ota`; the
  person uploads). It needs the `scripts` submodule and a `.env` with the OTA and portal passwords. Builds
  stamp the git commit (`FIRMWARE_GIT_REV`), shown at boot and in `/DIAG`.
- Its README documents the link, commands, settings and lessons learned (for example: never call `dacWrite()` from an
  interrupt).

## Writing style for docs

Plain, direct sentences; name things by what a user sees. Changelog and roadmap entries say what changed and why,
with enough detail to act on (the roadmap's What / How / Done when).
