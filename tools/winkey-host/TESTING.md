# Testing the keyer's Winkey emulation and USB port setting

How to check, on the hardware, three keyer changes and the host tool that tests them:

| Change | Branch | What it does |
|---|---|---|
| USB port setting | `feature/usb-port-mode` | Device > USB port: CLI or Winkey, saved, switched without a power cycle |
| Power-on button | `fix/power-on-serial-button` | Holding the command button at power-on gives the other USB port mode for that session (it never worked before: K3NG read the button before setting up the button ladder) |
| Farnsworth translation | `feature/winkey-farnsworth` | With `OPTION_FARNSWORTH_SETS_EFFECTIVE_SPEED`, a Winkey host's speed and Farnsworth mean what they mean on a K1EL WinKeyer |

The `w7yfr` build has all three, with Winkey emulation on and the port starting as the CLI until you change it.

## Required: only one program on the port

**Quit the CLI terminal (or `pio device monitor`, the Arduino serial monitor, a logging program) before running
the tool, every time.** macOS lets two programs open the same serial port, and when both do, they split what the
keyer sends between them: the tool misses answers and reports that the keyer didn't answer. The tool checks for this
before it starts and stops with the other program's name if the port is in use, and it holds the port to itself
while it runs. Steps 1, 2b and 7 use a terminal: quit it before the step that runs the tool.

## What you need

- The keyer on USB, flashed with the `w7yfr` build (`pio run -e w7yfr -t upload` in the keyer checkout).
- Python 3. The host tool (`winkey_host.py`, in this folder) needs no packages.
- The keyer checkout next to this repo (the usual workspace layout): the tool reads the keyer's port from its
  `platformio.ini` (`monitor_port` in `[env:w7yfr]`). Otherwise give `--port`; `winkey_host.py ports` lists ports
  and marks the keyer's.

Run the commands below from the workspace folder (the one holding `stellaluna/` and `k3ng_cw_keyer/`). Each run
of the tool resets the Mega (opening its port does that), waits 3 s for it to start, and tells the keyer the host
has closed when it's done.

## 1. Before changing anything: the CLI still works

1. Open a terminal on the keyer at 115200 baud (`pio device monitor` in the keyer checkout).
2. Type `\$ ky.usb`.
   - Expect `USB port: CLI`.
3. Quit the terminal.

## 2. Switching the USB port to Winkey

From the menu (or step 2b, from the CLI):

1. Enter command mode, key `/` and pause: the settings menu opens.
2. Open Device; the USB port row reads `CLI`.
3. `R` to change it, dit or dah to `Winkey`, `R` to save.
   - Expect the row to read `Winkey`. The port is now at 1200 baud and speaks the Winkey protocol: a terminal at
     115200 shows nothing useful.

2b. From the CLI instead: `\$ ky.usb winkey`.
   - Expect `USB port: Winkey` to print, then the terminal goes quiet (the port has switched). Quit the terminal.

## 3. The host tool connects

```sh
python3 stellaluna/tools/winkey-host/winkey_host.py check
```

Expect:

```
keyer port: ... (from k3ng_cw_keyer/platformio.ini, env w7yfr)
waiting 3 s for the keyer to restart (opening its port resets it)...
connected: the keyer answers as WinKeyer version 23
keyer settings, as a host reads them:
  speed       ...
...
disconnected
```

If it says the keyer didn't answer as a Winkey, the port is still in CLI mode (go back to step 2). The keyer
beeps when a host connects and when it disconnects.

## 4. The setting survives a power cycle

1. Power the keyer off and on.
2. Run `check` again.
   - Expect `connected`: the port started in Winkey mode.

## 5. The Farnsworth translation

```sh
python3 stellaluna/tools/winkey-host/winkey_host.py farnsworth
```

It does what a logging program would: sets speed 10 and Farnsworth 25 (on a WinKeyer: characters at 25, overall
10), reads them back, and times sending. The difference between the times of `0` and `E` gives the character
speed (both end with the same letter space, which Farnsworth stretches, so it cancels out); `PARIS PARIS` gives
the overall speed. Then it turns Farnsworth off and checks the characters drop to 10.
At the end it puts the keyer's speeds back.

Expect every line to say PASS and the last line to read `PASSED: 5 of 5 checks passed`. You should hear fast
characters with long gaps in the first part, then slow characters.

- The timings are measured over USB, so they're approximate (it allows 20%).
- It first waits for the keyer's startup "HI" to finish (about 6 s after connecting at 5 wpm). The keyer answers
  the host while it sounds HI, so anything sent meanwhile waits behind it, and its timing would include the rest of
  HI.
- A character speed near 10 in the first part means the speeds weren't translated.
- `--speed` and `--farnsworth` try other speeds (`farnsworth --speed 15 --farnsworth 30`).

## 6. The pots

```sh
python3 stellaluna/tools/winkey-host/winkey_host.py pots
```

How the pots behave while a host is connected (with `OPTION_FARNSWORTH_SETS_EFFECTIVE_SPEED`, as in `w7yfr`):

- A logging program knows one speed: the overall speed, the WPM number on its screen. It has no Farnsworth or
  character speed. Speed reports carry that number.
- Both pots set the keyer's speeds, as with no host connected (and as a WinKeyer's pot does): the speed pot the
  character speed, the Farnsworth pot the overall speed. The host is told whenever the overall speed changes.
- So: with Farnsworth off (the Farnsworth pot down, or at or above the speed pot), the speed pot is the overall
  speed and is reported. With Farnsworth on, the Farnsworth pot is reported, and the speed pot only changes how
  fast each character goes, which a host has nothing to show for, so it isn't reported.
- A host's own speed commands apply until a pot moves.
- A report can only say 5 to 68 wpm (the speed pot's low end and 63 above it); a speed below 5 reports as 5.

Each report prints as `keyer reports speed N wpm; the host shows it and sends speed N back` (the tool sends it
back as some logging programs do; it changes nothing, since the keyer is already at that speed). Ctrl-C stops it
and shows the settings it ended on.

Try this, in order:

1. Farnsworth pot all the way down (off).
2. Speed pot all the way up, then all the way down.
   - Expect a report for each step, 5 up to 35 and back down.
3. Speed pot to the middle (about 20).
   - Expect reports up to about 20.
4. Farnsworth pot slowly all the way up.
   - Expect reports of the Farnsworth pot's speed while it's below 20 (shown as 5 below 5), then one report of
     the speed pot's 20 when it passes it, and nothing more above that.
5. Farnsworth pot back to about 10: characters at 20, overall 10.
   - Expect reports on the way down, ending near 10.
6. Speed pot slowly up, then down to just above the Farnsworth pot.
   - Expect no reports: the character speed changes (key something to hear it), the overall speed doesn't.
7. Speed pot on down, below the Farnsworth pot, to the bottom.
   - Expect reports again once it's below: Farnsworth has gone off, and the speed pot is the host's speed.
8. Ctrl-C.
   - Expect the settings to show where the pots ended: `5 wpm (Farnsworth off)` after step 7.

## 7. Back to the CLI without the display: the command button at power-on

Opening the keyer's port (a terminal, `pio device monitor`, or this tool) restarts the keyer, and each restart reads
the command button again. So the button's CLI lasts only until the next program opens the port: hold the button
while you open the terminal, since that open is the restart.

1. Hold the command button.
2. While holding it, open the CLI: `pio device monitor -e w7yfr` in the keyer checkout (115200 baud).
3. Let go after a second (the keyer waits at startup until the button is released).
   - Expect K3NG's boot banner and a working CLI.
4. `\$ ky.usb`
   - Expect `USB port: CLI`: this session's mode.
5. Quit the monitor, then run `winkey_host.py check` (no button).
   - Expect `connected`: the saved setting is still Winkey.

## 8. Back to the CLI for good

1. Hold the button and open the monitor, as in step 7.
2. `\$ ky.usb cli`
   - Expect `USB port: CLI`.
3. Quit, and open the monitor again without the button.
   - Expect the CLI banner: the setting was saved.
4. Quit, and run `winkey_host.py check`.
   - Expect it to say the keyer didn't answer as a Winkey, and how to switch it.

(Or from the menu: Device > USB port > CLI, then the same checks from step 3.)

## Interactive mode

```sh
python3 stellaluna/tools/winkey-host/winkey_host.py
```

Connects, shows the settings, and gives a `winkey>` prompt. `help` lists the commands: `settings`, `speed N`,
`farnsworth N`, `send TEXT`, `clear`, `tune on`/`off`, `mode`, `sidetone N`, `weight N`, `raw HEX...`,
`verbose on`, `quit`. The keyer's status, echoed characters and speed reports print as they arrive.

## If something goes wrong

| What you see | Likely cause |
|---|---|
| `... isn't there: is the keyer plugged in?` | The keyer isn't on USB, or its port has another name: `winkey_host.py ports` |
| `... is open in another program: ...` | A terminal or monitor still has the port: quit it (it's named in the message) |
| `can't open ...: is a terminal or pio device monitor still using it?` | Another program has the port to itself: quit it |
| `the keyer didn't answer as a Winkey` | The USB port is in CLI mode (step 2), another program has the port (lsof couldn't tell), or the keyer is still starting: try again |
| `got N of 15 bytes back` | The keyer answered part of the request: run it again; if it repeats, note it with `-v` |
| Garbage in a 115200 terminal | The port is in Winkey mode (1200 baud): steps 7 and 8 get the CLI back |

`-v` on any task prints every byte each way; include that output when reporting a problem.

## Without the hardware

```sh
python3 stellaluna/tools/winkey-host/winkey_host.py selftest
```

Runs the tool against a fake keyer built into it, to check the tool itself. The fake doesn't send Morse at real
speeds, so the `farnsworth` timings can't be checked this way.
