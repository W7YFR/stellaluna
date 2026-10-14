# winkey-host

A small Winkey host for testing the keyer's Winkey emulation (`FEATURE_WINKEY_EMULATION`) without a logging program.
It talks to the keyer over its USB port the way N1MM or Win-Test does (the K1EL WinKeyer protocol), and shows what
the keyer says back. Python 3 only, no packages (macOS or Linux).

[TESTING.md](TESTING.md) walks through testing the keyer's Winkey mode, the USB port setting and the Farnsworth
translation on the hardware, step by step, with what to expect at each step.

## Before you start

- The keyer's USB port must be in Winkey mode: command mode, `/` and pause for the menu, then Device > USB port >
  Winkey. If it isn't, the tool says so.
- **Quit any terminal or `pio device monitor` on the port first.** macOS lets two programs open it, and they then
  split the keyer's answers. The tool refuses to start if another program has the port (naming it), and holds the
  port to itself while it runs.
- The port comes from the keyer's `platformio.ini` (`monitor_port` in `[env:w7yfr]`), so you don't need to give it.
  Use `--port` for another one; `ports` lists them and marks the keyer's.

Connecting resets the Mega (opening its port does that), so each run waits 3 s before talking, and tells the keyer
the host has closed when it's done.

## Tasks

Run from the workspace folder (or give the script's full path):

```sh
python3 stellaluna/tools/winkey-host/winkey_host.py              # connect and type commands (help lists them)
python3 stellaluna/tools/winkey-host/winkey_host.py check        # is it answering as a Winkey? shows its settings
python3 stellaluna/tools/winkey-host/winkey_host.py farnsworth   # tests the Farnsworth translation: PASS or FAIL
python3 stellaluna/tools/winkey-host/winkey_host.py pots         # shows what the keyer tells the host as you turn the pots
python3 stellaluna/tools/winkey-host/winkey_host.py send CQ TEST # sends text, and says how fast it went
python3 stellaluna/tools/winkey-host/winkey_host.py ports        # lists serial ports
python3 stellaluna/tools/winkey-host/winkey_host.py selftest     # against a built-in fake keyer, no hardware
```

`-v` shows every byte each way.

### farnsworth

Needs `OPTION_FARNSWORTH_SETS_EFFECTIVE_SPEED` in the keyer. It sets what a host would (speed 10, Farnsworth 25:
characters at 25, overall 10), reads it back, and times two things: the character speed and the overall speed
(`PARIS PARIS`). The keyer reports itself busy until the letter space after the last character, which Farnsworth
stretches, so one character's time isn't its speed. Instead it times `0` (19 dit units) and `E` (1): both end with
the same letter space, so the difference is 18 units at the character speed. Then it turns Farnsworth off
and checks the character speed drops to 10. Without the translation the characters would go at 10 throughout. It
puts the keyer's speeds back at the end. `--speed` and `--farnsworth` change the two speeds.

### pots

Prints each speed report the keyer sends as you turn the pots: these are what make a logging program's speed
display change. A logging program knows one speed, the overall speed, so that's what a report carries. With
`OPTION_FARNSWORTH_SETS_EFFECTIVE_SPEED`, both pots set the keyer's speeds while a host is connected (as a
WinKeyer's pot does), and the keyer reports the overall speed whenever it changes: the speed pot with Farnsworth
off, the Farnsworth pot with it on. The tool sends each report back as a speed command, as some logging programs
do (`--no-follow` doesn't). [TESTING.md](TESTING.md) step 6 has a sequence to try.
