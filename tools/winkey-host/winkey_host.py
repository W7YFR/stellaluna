#!/usr/bin/env python3
"""A small Winkey host, for testing the keyer's Winkey emulation without a logging program.

It talks to the keyer over its USB port the way a logging program (N1MM, Win-Test) does, using the K1EL WinKeyer
protocol, and shows what the keyer says back. Python 3 only, no packages (macOS or Linux).

  winkey_host.py               connect and type commands (type "help")
  winkey_host.py check         is the keyer answering as a Winkey? shows its settings
  winkey_host.py farnsworth    tests the Farnsworth translation, and says whether it passed
  winkey_host.py pots          shows what the keyer tells the host as you turn the pots
  winkey_host.py send CQ TEST  sends text
  winkey_host.py ports         lists serial ports

The port comes from the keyer's platformio.ini (env w7yfr's monitor_port) unless you give --port.
"""

import argparse
import configparser
import fcntl
import glob
import os
import queue
import select
import shlex
import subprocess
import sys
import termios
import threading
import time
import tty

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KEYER = os.path.normpath(os.path.join(HERE, "..", "..", "..", "k3ng_cw_keyer"))
BOOT_WAIT = 3.0  # opening the port resets a Mega; it takes about 2 s to start
STARTUP_SECONDS = 2.0  # from opening the port to the keyer starting to sound "HI" (generous)
HI_UNITS = 16  # "HI" and the letter space after each letter, in dit units

# Status bytes are 0b110xxxxx, speed pot bytes 0b10xxxxxx, anything else is an echoed character.
STATUS_BITS = [(1, "XOFF"), (2, "BREAKIN"), (4, "BUSY"), (8, "KEYDOWN"), (16, "WAIT")]

MODE_BITS = {
    "contest": 1, "autospace": 2, "serialecho": 4, "swap": 8, "paddleecho": 64, "nowatchdog": 128,
}
KEYER_MODES = {"b": 0, "a": 16, "ultimatic": 32, "bug": 48}

VALUE_NAMES = [
    "mode", "speed", "sidetone", "weight", "ptt lead", "ptt tail", "pot min", "pot range", "1st extension",
    "compensation", "farnsworth", "paddle setpoint", "dah:dit ratio", "pin config", "pot range (WK1)",
]

# Elements of each character, for estimating the sending speed of a timed message.
MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.", "G": "--.", "H": "....", "I": "..",
    "J": ".---", "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-", "5": ".....", "6": "-....",
    "7": "--...", "8": "---..", "9": "----.", "/": "-..-.", "?": "..--..", ".": ".-.-.-", ",": "--..--",
    "=": "-...-", "+": ".-.-.", "-": "-....-",
}

BAUDS = {1200: termios.B1200, 9600: termios.B9600, 115200: termios.B115200}


class WinkeyError(Exception):
    pass


def morse_units(text):
    """Dit units the text takes at standard spacing (PARIS is 43, plus 7 for a word space after it)."""
    words = [w for w in text.upper().split() if any(c in MORSE for c in w)]
    units = 7 * (len(words) - 1)
    for word in words:
        codes = [MORSE[c] for c in word if c in MORSE]
        units += sum(sum(1 if e == "." else 3 for e in code) + len(code) - 1 for code in codes)
        units += 3 * (len(codes) - 1)
    return units


def describe_status(b):
    bits = [name for bit, name in STATUS_BITS if b & bit]
    return "status: " + (" ".join(bits) if bits else "idle")


def describe_mode(value):
    names = [name for name, bit in MODE_BITS.items() if value & bit]
    keyer = {0: "iambic B", 16: "iambic A", 32: "ultimatic", 48: "bug"}[value & 48]
    return ", ".join([keyer] + names)


def describe_speeds(speed, farnsworth):
    """K1EL's meaning: speed is the overall speed; Farnsworth above it is the character speed."""
    if farnsworth and farnsworth > speed:
        return "characters at %d wpm, overall %d wpm (Farnsworth on)" % (farnsworth, speed)
    return "%d wpm (Farnsworth off)" % speed


# ----- finding the port

def platformio_port(keyer, env):
    """The keyer's port as its platformio.ini names it: [env:<env>] monitor_port or upload_port, else [env]'s."""
    path = os.path.join(keyer, "platformio.ini")
    if not os.path.exists(path):
        return None, path
    ini = configparser.ConfigParser(interpolation=None, strict=False)
    ini.read(path)
    for section in ("env:" + env, "env"):
        for key in ("monitor_port", "upload_port"):
            if ini.has_option(section, key):
                return ini.get(section, key).split(";")[0].strip(), path
    return None, path


def short(path):
    """A path relative to the workspace folder (the one holding the keyer checkout), for messages."""
    return os.path.relpath(path, os.path.dirname(DEFAULT_KEYER))


def serial_ports():
    return sorted(glob.glob("/dev/cu.*") + glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))


def find_port(args):
    if args.port:
        return args.port, "--port"
    port, path = platformio_port(args.keyer, args.env)
    if port:
        return port, "%s, env %s" % (short(path), args.env)
    raise WinkeyError("no port given, and %s doesn't name one (monitor_port in [env:%s]).\n"
                      "Give it with --port; the serial ports here are:\n  %s"
                      % (path, args.env, "\n  ".join(serial_ports()) or "(none)"))


def port_users(path):
    """Other programs holding the port open, as "name (pid)", if lsof can tell."""
    try:
        out = subprocess.run(["lsof", "-F", "pc", path], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    users, pid = [], None
    for line in out.splitlines():
        if line.startswith("p"):
            pid = line[1:]
        elif line.startswith("c") and pid and int(pid) != os.getpid():
            users.append("%s (pid %s)" % (line[1:], pid))
    return users


class Port:
    """A raw serial port (or pty) opened with termios, held exclusively while it's open."""

    def __init__(self, path, baud, check_users=True):
        users = port_users(path) if check_users else []
        if users:
            raise WinkeyError("%s is open in another program: %s.\nClose it first (quit the CLI terminal or pio "
                              "device monitor): two programs on the port split the keyer's answers between them."
                              % (path, ", ".join(users)))
        try:
            self.fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        except FileNotFoundError:
            raise WinkeyError("%s isn't there: is the keyer plugged in? Serial ports here:\n  %s"
                              % (path, "\n  ".join(serial_ports()) or "(none)"))
        except OSError as e:
            raise WinkeyError("can't open %s (%s): is a terminal or pio device monitor still using it?"
                              % (path, e.strerror))
        try:
            fcntl.ioctl(self.fd, termios.TIOCEXCL)  # nobody else opens it while we have it
        except (AttributeError, OSError):
            pass
        tty.setraw(self.fd)
        attrs = termios.tcgetattr(self.fd)
        attrs[2] |= termios.CLOCAL | termios.CREAD
        attrs[2] &= ~termios.CSTOPB  # one stop bit, as the Arduino sends; a WinKeyer's two read fine as one
        attrs[4] = attrs[5] = BAUDS[baud]
        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        termios.tcflush(self.fd, termios.TCIOFLUSH)

    def write(self, data):
        view = memoryview(bytes(data))
        while view:
            select.select([], [self.fd], [], 1.0)
            try:
                n = os.write(self.fd, view)
            except BlockingIOError:
                continue
            view = view[n:]

    def read(self, timeout):
        try:
            ready, _, _ = select.select([self.fd], [], [], timeout)
            return os.read(self.fd, 256) if ready else b""
        except (BlockingIOError, OSError, ValueError):
            return b""

    def discard_input(self):
        termios.tcflush(self.fd, termios.TCIFLUSH)

    def close(self):
        os.close(self.fd)


class WinkeyHost:
    def __init__(self, port, verbose=False, out=print):
        self.port = port
        self.verbose = verbose
        self.out = out
        self.quiet_status = False  # don't print status bytes (the tests watch them themselves)
        self.follow_pot = False  # send a reported speed back, as a logging program that follows the pot does
        self.replies = queue.Queue()  # bytes answering a command we sent (version, values, echo test)
        self.expecting = 0
        self.lock = threading.Lock()
        self.status = 0xC0
        self.status_changed = threading.Condition()
        self.echo = []  # characters echoed since the last print
        self.running = True
        self.is_open = False
        self.opened_at = time.time()  # the Mega restarts when its port opens
        self.values = None
        self.pot_min = 5
        self.mode = None
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()

    def stop(self):
        """Stop reading, then close the port (closing it under the reader broke its select)."""
        self.running = False
        self.reader.join(1.0)
        self.port.close()

    # ----- incoming

    def _read_loop(self):
        while self.running:
            data = self.port.read(0.1)
            if not data:
                if not self.status & 4:  # not sending: a pause mid-message isn't the end of it
                    self._flush_echo()
                continue
            for b in data:
                self._incoming(b)

    def _incoming(self, b):
        if self.verbose:
            self.out("  <- 0x%02X" % b)
        with self.lock:
            if self.expecting > 0:
                self.expecting -= 1
                self.replies.put(b)
                return
        if b & 0xC0 == 0xC0:
            if not b & 4:
                self._flush_echo()  # the message is done; keep its echo ahead of the idle status
            with self.status_changed:
                self.status = b
                self.status_changed.notify_all()
            if not self.quiet_status:
                self.out("  keyer " + describe_status(b))
        elif b & 0xC0 == 0x80:
            self._flush_echo()
            wpm = (b & 0x3F) + self.pot_min
            if self.follow_pot:
                self.send(0x02, wpm)
                self.out("  keyer reports speed %d wpm; the host shows it and sends speed %d back" % (wpm, wpm))
            else:
                self.out("  keyer reports speed %d wpm: a host would now show %d wpm" % (wpm, wpm))
        else:
            self.echo.append(chr(b) if 32 <= b < 127 else "<0x%02X>" % b)
            if b == 32 or len(self.echo) > 40:
                self._flush_echo()

    def _flush_echo(self):
        if self.echo:
            self.out("  keyer sent: " + "".join(self.echo))
            self.echo = []

    # ----- outgoing

    def send(self, *data):
        if self.verbose:
            self.out("  -> " + " ".join("0x%02X" % b for b in data))
        self.port.write(bytes(data))

    def request(self, data, count, timeout=1.5):
        """Send a command and collect the count bytes that answer it."""
        while not self.replies.empty():
            self.replies.get_nowait()
        with self.lock:
            self.expecting = count
        self.send(*data)
        got = []
        deadline = time.time() + timeout + count * 0.01
        while len(got) < count:
            try:
                got.append(self.replies.get(timeout=max(0.0, deadline - time.time())))
            except queue.Empty:
                break
        with self.lock:
            self.expecting = 0
        return got

    def wait_status(self, test, timeout):
        deadline = time.time() + timeout
        with self.status_changed:
            while not test(self.status):
                left = deadline - time.time()
                if left <= 0:
                    return False
                self.status_changed.wait(left)
        return True

    def send_text(self, text):
        """Buffered text, a byte at a time, holding off while the keyer says XOFF."""
        for ch in text.upper():
            if self.status & 1:
                self.wait_status(lambda s: not s & 1, 30)
            self.send(ord(ch))
            time.sleep(0.01)

    # ----- the protocol

    def host_open(self):
        got = self.request([0x00, 0x02], 1)
        if got and not 10 <= got[0] <= 40:  # WinKeyer 1 says 10, 2 says 20-23 (K3NG 23), 3 says 30-31
            time.sleep(0.5)
            got = []  # junk, not a version: most likely the CLI at 115200 baud
        if not got:
            raise WinkeyError(
                "the keyer didn't answer as a Winkey. Its USB port is probably in CLI mode: on the keyer, enter\n"
                "command mode, key / and pause for the menu, then Device > USB port > Winkey. (Holding the\n"
                "command button at power-on also gives the other mode, for that session.)")
        self.is_open = True
        return got[0]

    def host_close(self):
        if self.is_open:
            self.send(0x00, 0x03)
            self.is_open = False

    def get_values(self):
        got = self.request([0x00, 0x07], 15)
        if len(got) < 15:
            raise WinkeyError("asked for the keyer's settings and got %d of 15 bytes back" % len(got))
        self.values = dict(zip(VALUE_NAMES, got))
        self.mode = got[0]
        self.pot_min = got[6]
        return self.values

    def speeds(self):
        v = self.get_values()
        return v["speed"], v["farnsworth"]

    def set_speed(self, wpm):
        self.send(0x02, wpm)

    def set_farnsworth(self, wpm):
        self.send(0x0D, wpm)

    def busy_seconds(self, text):
        """Send text and time it from BUSY to idle, or None. The keyer stays BUSY through the letter space after
        the last character, which Farnsworth stretches."""
        self.wait_status(lambda s: not s & 4, 5)
        self.send_text(text)
        if not self.wait_status(lambda s: s & 4, 5):
            return None
        start = time.time()
        if not self.wait_status(lambda s: not s & 4, 300):
            return None
        return time.time() - start

    def wait_for_startup(self, wpm):
        """The keyer sounds "HI" at power-on, at its speed, and keeps answering the host meanwhile, so anything
        timed before HI is over includes the rest of it (4 s at 5 wpm). Wait it out."""
        left = self.opened_at + STARTUP_SECONDS + HI_UNITS * 1.2 / max(1, wpm) - time.time()
        if left > 0:
            self.out("     waiting %.1f s for the keyer's startup HI to finish..." % left)
            time.sleep(left)

    def timed_send(self, text):
        """Send text: about the overall wpm it went at, or None."""
        seconds = self.busy_seconds(text)
        return 1.2 * morse_units(text) / seconds if seconds else None

    def character_speed(self):
        """The character speed: 0 (19 dit units) and E (1) each end with the same letter space, so the difference
        in their times is 18 units at the character speed, with the space and the USB delays taken out."""
        zero, e = self.busy_seconds("0"), self.busy_seconds("E")
        if self.verbose:
            self.out("       timings: 0 took %s s, E took %s s (at characters 25 the 0 is 0.91 s and the E 0.05 s,"
                     " plus the same letter space after each)" % (zero and "%.2f" % zero, e and "%.2f" % e))
        if not zero or not e or zero <= e:
            return None
        return 1.2 * 18 / (zero - e)


# ----- tasks

def connect(args, out=print):
    port_name, source = find_port(args)
    out("keyer port: %s (from %s)" % (port_name, source))
    port = Port(port_name, args.baud)
    opened_at = time.time()
    out("waiting %.0f s for the keyer to restart (opening its port resets it)..." % args.boot_wait)
    time.sleep(args.boot_wait)
    port.discard_input()  # in CLI mode the startup banner arrives as junk at this baud rate
    host = WinkeyHost(port, verbose=args.verbose, out=out)
    host.opened_at = opened_at
    version = host.host_open()
    out("connected: the keyer answers as WinKeyer version %d" % version)
    return host


def show_settings(host):
    v = host.get_values()
    host.out("keyer settings, as a host reads them:")
    host.out("  speed       %s" % describe_speeds(v["speed"], v["farnsworth"]))
    host.out("  keyer mode  %s" % describe_mode(v["mode"]))
    host.out("  speed pot   %d to %d wpm" % (v["pot min"], v["pot min"] + v["pot range"]))
    host.out("  weight %d, sidetone setting %d, ptt lead %d, ptt tail %d"
             % (v["weight"], v["sidetone"], v["ptt lead"], v["ptt tail"]))


def task_check(host, args):
    show_settings(host)
    return True


def task_send(host, args):
    text = " ".join(args.text)
    host.wait_for_startup(host.speeds()[0])
    host.out("sending %r..." % text)
    wpm = host.timed_send(text)
    host.out("done%s" % ((": about %.1f wpm overall" % wpm) if wpm else ""))
    return True


def task_pots(host, args):
    host.follow_pot = not args.no_follow
    show_settings(host)
    host.out("""
Turn the pots; each speed the keyer reports to the host shows below. Ctrl-C to stop (then it reads the
settings back, so you can see where the speeds ended up).
- A host knows one speed, the overall speed; reports carry it. Both pots set the keyer's speeds.
- Farnsworth off: the speed pot is the overall speed, and is reported.
- Farnsworth on: the Farnsworth pot is the overall speed, and is reported; the speed pot only changes the
  character speed, which a host has nothing to show for.
- %s""" % ("Each report is sent back as a speed command, as some logging programs do (--no-follow: don't)."
           if host.follow_pot else "Reports aren't sent back (--no-follow)."))
    try:
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        host.out("")
    host.follow_pot = False
    time.sleep(0.3)
    show_settings(host)
    return True


def task_farnsworth(host, args):
    """Speed 10, Farnsworth 25 should send characters at 25 and overall at 10; untranslated, both come out 10."""
    host.quiet_status = True
    speed, farnsworth = args.speed, args.farnsworth
    before = host.speeds()
    host.out("the keyer is at: %s" % describe_speeds(*before))
    host.wait_for_startup(before[0])
    results = []

    def check(name, ok, detail):
        results.append(ok)
        host.out("  %-4s %s: %s" % ("PASS" if ok else "FAIL", name, detail))

    def near(measured, wanted):
        return measured is not None and abs(measured - wanted) <= 0.2 * wanted

    def show(wpm):
        return "%.1f wpm" % wpm if wpm else "no answer"

    try:
        host.out("\n1. A host sets speed %d and Farnsworth %d: characters at %d, overall %d."
                 % (speed, farnsworth, farnsworth, speed))
        host.set_speed(speed)
        host.set_farnsworth(farnsworth)
        time.sleep(0.2)
        got = host.speeds()
        check("reads back", got == (speed, farnsworth), "speed %d, Farnsworth %d" % got)
        host.out("     sending 0 and E (the difference in their times gives the character speed)...")
        char = host.character_speed()
        check("character speed", near(char, farnsworth), "%s, want about %d" % (show(char), farnsworth))
        host.out("     sending PARIS PARIS (overall speed)...")
        overall = host.timed_send("PARIS PARIS")
        check("overall speed", near(overall, speed), "%s, want about %d" % (show(overall), speed))

        host.out("\n2. The host turns Farnsworth off (0): everything at %d." % speed)
        host.set_farnsworth(0)
        time.sleep(0.2)
        got = host.speeds()
        check("reads back", got[0] == speed and got[1] <= speed, "speed %d, Farnsworth %d" % got)
        char = host.character_speed()
        check("character speed", near(char, speed), "%s, want about %d" % (show(char), speed))
    finally:
        host.set_speed(before[0])
        host.set_farnsworth(before[1])
        time.sleep(0.2)
        host.out("\nput back: %s" % describe_speeds(*host.speeds()))

    passed = all(results)
    host.out("\n%s: %d of %d checks passed" % ("PASSED" if passed else "FAILED", sum(results), len(results)))
    if not passed:
        host.out("(Timing is measured over USB, so allow a little slack; a character speed of %d instead of %d\n"
                 "means the speeds weren't translated.)" % (speed, farnsworth))
    return passed


SHELL_HELP = """  settings          the keyer's settings, as a host reads them
  speed N           set the speed (0 = follow the speed pot)
  farnsworth N      set the Farnsworth speed (the character speed, above the speed; 0 = off)
  send TEXT         send text, and say how fast it went
  clear             stop sending
  tune on | off     key down / key up
  mode ...          keyer mode: b, a, ultimatic, bug; +paddleecho, -paddleecho, +swap, ...
  sidetone N        sidetone setting, 1-10
  weight N          weighting, 10-90
  raw HEX ...       send bytes as they are (raw 02 14)
  verbose on | off  show every byte
  quit              disconnect (the keyer is told the host has closed)"""


def shell_command(host, line):
    words = shlex.split(line)
    if not words:
        return True
    cmd, args = words[0].lower(), words[1:]
    num = lambda i: int(args[i], 0)
    if cmd in ("quit", "exit", "q"):
        return False
    elif cmd in ("help", "?"):
        host.out(SHELL_HELP)
    elif cmd in ("settings", "values"):
        show_settings(host)
    elif cmd in ("speed", "wpm"):
        host.set_speed(num(0))
    elif cmd in ("farnsworth", "fw"):
        host.set_farnsworth(num(0))
    elif cmd == "send":
        wpm = host.timed_send(" ".join(args))
        if wpm:
            host.out("  about %.1f wpm overall" % wpm)
    elif cmd == "clear":
        host.send(0x0A)
    elif cmd == "tune":
        host.send(0x0B, 1 if args and args[0].lower() == "on" else 0)
    elif cmd == "mode":
        mode = host.mode or 0
        for arg in args:
            if arg.lower() in KEYER_MODES:
                mode = (mode & ~48) | KEYER_MODES[arg.lower()]
            elif arg[:1] in "+-" and arg[1:].lower() in MODE_BITS:
                bit = MODE_BITS[arg[1:].lower()]
                mode = (mode | bit) if arg[0] == "+" else (mode & ~bit)
            else:
                host.out("  unknown: %s" % arg)
                return True
        host.mode = mode
        host.send(0x0E, mode)
        host.out("  mode: %s" % describe_mode(mode))
    elif cmd == "sidetone":
        host.send(0x01, num(0))
    elif cmd == "weight":
        host.send(0x03, num(0))
    elif cmd == "raw":
        host.send(*[int(a, 16) for a in args])
    elif cmd == "verbose":
        host.verbose = not args or args[0].lower() == "on"
    else:
        host.out("  unknown command %r; type help" % cmd)
    return True


def task_shell(host, args):
    show_settings(host)
    host.out("\ntype help for commands, quit to disconnect")
    while True:
        try:
            line = input("winkey> ")
        except EOFError:
            break
        try:
            if not shell_command(host, line):
                break
        except (ValueError, IndexError) as e:
            host.out("  bad arguments: %s" % e)
    return True


def task_ports(args):
    port, path = platformio_port(args.keyer, args.env)
    for p in serial_ports():
        print("%s%s" % (p, "   <- the keyer, per %s" % short(path) if p == port else ""))
    if port and port not in serial_ports():
        print("(%s names %s, which isn't plugged in)" % (short(path), port))
    return True


# ----- self test: a fake keyer on a pty, answering the way K3NG's emulation does

class FakeKeyer(threading.Thread):
    def __init__(self, fd):
        super().__init__(daemon=True)
        self.fd = fd
        self.values = [0, 20, 5, 50, 0, 0, 5, 30, 0, 0, 0, 50, 50, 6, 0]
        self.pending = []  # (command, bytes wanted, bytes so far)
        self.idle_timer = None

    def put(self, *data):
        os.write(self.fd, bytes(data))

    def run(self):
        while True:
            try:
                data = os.read(self.fd, 64)
            except OSError:
                return
            for b in data:
                self.byte(b)

    def byte(self, b):
        if self.pending:
            cmd, want, got = self.pending[-1]
            got.append(b)
            if len(got) < want:
                return
            self.pending.pop()
            self.command(cmd, got)
            return
        if b >= 0x20:  # like K3NG: BUSY when sending starts, each character echoed, idle when the buffer empties
            if self.idle_timer is None:
                self.put(0xC4)
            else:
                self.idle_timer.cancel()
            self.put(b)
            self.idle_timer = threading.Timer(0.3, self.done_sending)
            self.idle_timer.start()
            return
        wants = {0x00: 1, 0x01: 1, 0x02: 1, 0x03: 1, 0x05: 3, 0x0D: 1, 0x0E: 1, 0x0F: 15}
        if b in wants:
            self.pending.append((b, wants[b], []))
        elif b == 0x15:
            self.put(0xC0)
        elif b == 0x07:
            self.put(0x80 | (self.values[1] - self.values[6]))

    def done_sending(self):
        self.idle_timer = None
        self.put(0xC0)

    def command(self, cmd, args):
        if cmd == 0x00 and args[0] == 0x02:
            self.put(23)
        elif cmd == 0x00 and args[0] == 0x07:
            self.put(*self.values)
        elif cmd == 0x02:
            self.values[1] = args[0]
        elif cmd == 0x0D:
            self.values[10] = args[0]
        elif cmd == 0x0E:
            self.values[0] = args[0]


def selftest():
    import pty
    master, slave = pty.openpty()
    FakeKeyer(master).start()
    lines = []
    out = lambda s: (lines.append(s), print(s))
    host = WinkeyHost(Port(os.ttyname(slave), 1200, check_users=False), out=out)
    host.host_open()
    show_settings(host)
    for line in ["speed 10", "farnsworth 25", "settings", "mode a +paddleecho", "send CQ", "raw 07"]:
        out("winkey> " + line)
        shell_command(host, line)
        time.sleep(0.4)
    host.host_close()
    host.stop()
    text = "\n".join(lines)
    checks = [
        ("settings read", "speed       20 wpm (Farnsworth off)" in text),
        ("Farnsworth read the K1EL way", "characters at 25 wpm, overall 10 wpm" in text),
        ("mode", "iambic A, paddleecho" in text),
        ("echo", "keyer sent: CQ" in text),
        ("speed report", "keyer reports speed 10 wpm" in text),
        ("timing math", morse_units("PARIS PARIS") == 93 and morse_units("0") == 19),
    ]
    print()
    for name, ok in checks:
        print("%-30s %s" % (name, "ok" if ok else "FAIL"))
    return all(ok for _, ok in checks)


TASKS = {"check": task_check, "farnsworth": task_farnsworth, "pots": task_pots, "send": task_send,
         "shell": task_shell}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", nargs="?", default="shell",
                    choices=sorted(list(TASKS) + ["ports", "selftest"]), help="what to do (default: shell)")
    ap.add_argument("text", nargs="*", help="for send: the text")
    ap.add_argument("-p", "--port", help="the keyer's serial port (default: from its platformio.ini)")
    ap.add_argument("--keyer", default=DEFAULT_KEYER, help="the keyer checkout (default: %(default)s)")
    ap.add_argument("--env", default="w7yfr", help="platformio.ini environment for the port (default: w7yfr)")
    ap.add_argument("--no-follow", action="store_true", help="pots: don't send reported speeds back")
    ap.add_argument("--speed", type=int, default=10, help="farnsworth test: the host's speed (default 10)")
    ap.add_argument("--farnsworth", type=int, default=25, help="farnsworth test: its Farnsworth (default 25)")
    ap.add_argument("-b", "--baud", type=int, default=1200, choices=sorted(BAUDS), help=argparse.SUPPRESS)
    ap.add_argument("--boot-wait", type=float, default=BOOT_WAIT, help=argparse.SUPPRESS)
    ap.add_argument("-v", "--verbose", action="store_true", help="show every byte")
    args = ap.parse_args()

    if args.task == "selftest":
        return 0 if selftest() else 1
    if args.task == "ports":
        task_ports(args)
        return 0
    if args.task == "send" and not args.text:
        ap.error("send needs the text: winkey_host.py send CQ TEST")

    host = None
    try:
        host = connect(args)
        return 0 if TASKS[args.task](host, args) else 1
    except WinkeyError as e:
        print("\n" + str(e))
        return 2
    except KeyboardInterrupt:
        return 130
    finally:
        if host:
            host.host_close()
            time.sleep(0.2)
            host.stop()
            print("disconnected")


if __name__ == "__main__":
    sys.exit(main())
