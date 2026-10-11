# keyer-build

Builds the K3NG keyer firmware from any checkout or worktree, on any branch, without uploading. Upstream `master`
(and feature branches cut from it) has no PlatformIO setup, so `keyer-build.py`:

1. copies the checkout's `k3ng_keyer/` sketch to a scratch folder (`$TMPDIR/stellaluna-keyer-build/`; PlatformIO's
   library cache there is kept between runs);
2. adds a known `platformio.ini` (ATmega2560 unless the preset says otherwise, the checkout's `libraries/`);
3. applies the three small fixes PlatformIO builds need, only where the branch doesn't have them already
   (`lcd_center_print_timed_wpm` and `NETWORK_CLIENT_CLS` from `build/platformio`, `convert_prosign` from
   `fix/prosign-forward-declaration`);
4. applies the preset's feature toggles to the copy, and builds;
5. prints one line per build: ok or FAIL, RAM and flash use, the first errors, and the log's path.

```sh
make keyer-build                                         # as-is preset on ../k3ng_cw_keyer
make keyer-build KEYER=/path/to/worktree PRESET=w7yfr-features ARGS='-D FEATURE_NEW_THING'
make keyer-matrix                                        # every preset in presets/matrix.txt
python3 tools/keyer-build/keyer-build.py --help          # all options (-D, -U, --set, -v, --list)
```

## Presets

Text files in `presets/`, one directive per line:

| Line | Meaning |
|---|---|
| `board <name>` | PlatformIO board (`megaatmega2560`, `nanoatmega328`, ...) |
| `hardware HARDWARE_xxx` | Select one of K3NG's hardware profiles (its own `keyer_*_xxx.h` files) |
| `include <preset>` | Start from another preset |
| `+NAME` | Define `NAME` (`-D NAME`) |
| `-NAME` | Comment out `NAME`'s `#define` in the copy |
| `=NAME VALUE` | Set a valued `#define` in the copy (for example `=NUMBER_OF_EXTRA_BUTTONS 2`) |
| `lib <library>` | An extra PlatformIO library the profile needs (for example `lib arduino-libraries/Ethernet`) |
| `flag <flag>` | An extra compiler flag (for example `flag -Wno-narrowing`) |

| Preset | Use it for |
|---|---|
| `as-is` | The checkout's own configuration. On the `w7yfr` checkout, that's the Stellaluna build |
| `w7yfr-features` | A branch cut from `master`, with the Stellaluna build's features turned on |
| `w7yfr-nodisp`, `w7yfr-nocli`, `w7yfr-novband` | The Stellaluna build without the display, CLI, or VBand link (run on `w7yfr`) |
| `test-everything` | K3NG's compile-everything profile: catches options missing from the other boards' files |
| `megakeyer`, `nanokeyer-rev-d` | Other boards' profiles, on a Mega and on an ATmega328 |

## When to run what

While working on a change, build only when it's worth checking, with the one preset that matters. Run the matrix
once, when the change is believed done.

`make keyer-matrix` runs with `--compare master`: each preset is also built on `master` (once per `master` commit;
the results are cached), and errors `master` already has don't count. Each line then reads:
- `ok`: builds.
- `old`: fails, but only with errors `master` has too (expected for some other boards' profiles: upstream builds with
  the Arduino IDE, and PlatformIO's prototype scanner misses some of its functions).
- `FAIL`: has errors `master` doesn't. These are the ones to fix.

`--compare <ref>` works with any branch or commit, for example the branch a feature was cut from.
