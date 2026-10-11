# Roadmap

Future work across the Stellaluna Keyer: the hardware (this repo), the keyer fork
([W7YFR/k3ng_cw_keyer](https://github.com/W7YFR/k3ng_cw_keyer), branch `w7yfr`) and the VBand adapter
([W7YFR/k3ng-vband-adapter](https://github.com/W7YFR/k3ng-vband-adapter)). Not in priority order. When an item is
done, move it into the right changelog and delete it here.

Each item says which parts it touches (**keyer**, **adapter**, **hardware**) and has:
- **What:** the problem or the feature, as you'd notice it using the keyer.
- **How:** what to change, and anything already known about where.
- **Done when:** how to tell it works.

## Bugs

All firmware; no hardware bugs are open.

### Settings don't persist across power cycles (keyer)
- **What:** some settings changed in the menu are lost at power-off. Paddle echo has to be turned back on after every
  power-on.
- **How:** paddle echo (`ky.echo`) is saved outside K3NG's `configuration` struct, in the spare EEPROM byte at
  `sizeof(configuration)+1` (the memories start at `+5`). Check that the byte is written when the setting changes, and
  that it's read back at boot after whatever sets paddle echo's default (otherwise the default overwrites it). Then
  check every other setting the menu can change: the ones inside `configuration` rely on K3NG's delayed config write
  (`config_dirty`), which may not be triggered by the menu's changes.
- **Done when:** each keyer setting changed from the menu survives a power cycle.

### The VBand menu breaks when the adapter powers off (keyer)
- **What:** the VBand settings and commands only exist while the ESP32 is on. With the menu open, powering the
  ESP32 off with its button leaves the VBand part of the menu open but broken.
- **How:** the adapter sends `BYE,OFF` before it powers off, and the link drops after. When either happens while the
  menu is in the VBand group, leave the group: back to the top level with a short "Adapter off" message. While the
  link is down, either hide the VBand group or show it with a single row explaining the adapter is off (or "Power
  on", once the keyer can power the ESP32 on; see below).
- **Done when:** powering the adapter off from inside its menu lands back on the top level with the message, and the
  menu keeps working.

### The LED shows a connection problem while VBand messages keep playing (adapter)
- **What:** the LED starts flashing (connection lost), but received code keeps playing and appearing on the display
  for a while.
- **How:** most likely the playback queue draining: received elements play at the sender's own speed, and the
  queue (up to 128 elements) isn't cleared on disconnect, so a long fast message can run well behind. First check:
  the playback should stop within about 10 s of the LED flashing; anything longer is a real bug. Then decide whether
  to keep draining (you hear the end of what was sent) or clear the queue on disconnect (silence matches the LED).
- **Done when:** the behavior is confirmed and the choice made; if clearing, playback stops when the LED starts
  flashing.

### The keyer doesn't build without a display (keyer)
- **What:** the Stellaluna build with `FEATURE_OLED_SSD1306` turned off fails to link: `undefined reference to
  ssd1306_clear_display()` and `ssd1306_toggle_display()`. Found by the `w7yfr-nodisp` preset.
- **How:** the extra button's display toggle and clear (commit `bb64cea`, made directly on `w7yfr`) call the OLED
  functions without checking the OLED is in the build. Wrap those calls in `#if defined(FEATURE_OLED_SSD1306)` (or
  give them a no-display fallback). Best done on `feature/extra-button` or a small fix branch, so the fix is
  mergeable on its own.
- **Done when:** `make keyer-build PRESET=w7yfr-nodisp` builds.

### The keyer doesn't build without the CLI (keyer, probably upstream)
- **What:** turning off `FEATURE_COMMAND_LINE_INTERFACE` fails with `'cli_straight_key_echo' was not declared` when
  `FEATURE_STRAIGHT_KEY_ECHO` and a display are on. Found by the `w7yfr-nocli` preset.
- **How:** `cli_straight_key_echo` is only declared with the CLI, but the display's straight-key echo uses it.
  Upstream `master` has the same code, so first confirm it fails there too (`make keyer-build
  KEYER=<master worktree> PRESET=w7yfr-features ARGS='-U FEATURE_COMMAND_LINE_INTERFACE'`). Fix by declaring it
  whenever `FEATURE_STRAIGHT_KEY_ECHO` is on; if it's upstream's, on its own `fix/` branch from `master`.
- **Done when:** `make keyer-build PRESET=w7yfr-nocli` builds.

### "Room X: N others" logs twice after each join (adapter)
- **What:** the line appears twice in the serial log (two user-list replies arrive). Nothing visible on the keyer.
- **How:** print it once per join (track the last count printed, or print only from the first reply).
- **Done when:** one line per join.

## Features: firmware only

### Forward the ESP32's log to the keyer's USB port (keyer, adapter)
- **What:** in its case only the keyer's USB-C port can be reached, not the ESP32's, so the adapter's serial log
  (the `DIAG` lines, connection events) can't be seen without opening it up. Stream it over the existing link and
  out of the keyer's USB port instead.
- **How:**
  - Adapter: route its `Serial.print` output through one log function that also queues each line for the link
    when forwarding is on. Send lines as a new frame type (`LG,<text>`), split to fit the 64-byte frame limit.
    Keep a small ring buffer of recent lines (a couple of KB) and send it first when forwarding turns on, so you see
    what happened before you plugged in.
  - Keyer: print each `LG` frame to its USB serial port, prefixed (`ESP> `).
  - Turn it on and off as an adapter setting (`vb.log`, default off, not saved), so it works from the CLI
    (`\$ vb.log 1`) and the menu.
  - The link is 38400 baud shared with received text and status screens: rate-limit the log, send it only when
    nothing else is waiting, and drop lines with a "(N lines dropped)" note rather than delay link traffic.
  - Both sides already ignore frame types they don't know, so this needs no link protocol version bump.
- **Done when:** with the keyer on USB and `vb.log` on, the adapter's log (including the recent history) appears in
  a serial monitor on the keyer's port, and keying, received text and status screens are unaffected.

### Dit hold opens the settings menu (keyer)
- **What:** holding the dit paddle for a run of dits currently clears or resets the display, after 10 dits. Make
  it open the settings menu instead, after 8 dits.
- **How:** the dit-hold detection is the fork's `FEATURE_DIT_HOLD_RESET`. Change the count to 8 and the action to
  entering command mode with the menu open. Clearing the display stays on the extra button.
- **Done when:** 8 dits in a row open the menu from normal sending, and nothing else changes.

### A clearer settings menu (keyer, adapter)
- **What:** the menu feels hectic. Give it more hierarchy and order it by what's used most, not by which board owns
  the setting.
- **How:**
  - First, move the keyer's settings table (`settings_keyer_items` and its labels) to `PROGMEM`. The build is at
    about 51.5% RAM (3.9 KB free), and more groups and labels won't fit otherwise.
  - Then agree on the structure before building it. For example: top level Speed and keying, Sidetone, VBand
    (Connect or Disconnect, Commands, Settings), Memories, Advanced; the most-used rows first in each group.
  - The adapter's settings may need a group field in the `SI` items so the keyer can place them, which is a link
    protocol change.
- **Done when:** the agreed structure is in, and everything reachable today is still reachable.

### Training menu with Q-codes (keyer)
- **What:** training from the menu, without a computer: Q-code practice, plus the other trainers K3NG has.
- **How:** the fork's paddle-only echo practice already plays a word, waits for you to send it back and shows the
  target on the display. Add a Q-code list (QTH, QRZ, QSL, QRM, QSB, QRS, ...) to it, and show each code's meaning
  after a correct answer. Add a Training group to the menu that starts this and the existing K3NG trainers. Check the
  RAM cost of each (word lists should live in `PROGMEM`).
- **Done when:** Q-code practice and the other trainers start from the menu and exit cleanly back to it.

### Farnsworth pot the other way round (keyer)
- **What:** today the main speed knob sets the overall (effective) speed and the Farnsworth knob sets a faster
  character speed. The expected way: the WPM knob sets the character speed only, and the Farnsworth knob sets the
  effective speed. With WPM at 25 and Farnsworth at 10, paddle keying sends characters at 25 and memories go out at
  an effective 10. A Farnsworth setting at or above the character speed means no Farnsworth.
- **How:** K3NG times paddle elements from `configuration.wpm` and stretches spacing only when
  `wpm_farnsworth > wpm`. So it isn't just swapping the two pots: paddle timing has to follow the character speed
  (the WPM knob), and memories and buffered sending use the character speed for elements with spacing stretched to
  the Farnsworth knob's effective speed. Do it as an option (for example
  `OPTION_FARNSWORTH_POT_SETS_EFFECTIVE_SPEED`) so upstream's behavior stays available, and update the display labels
  and the `ky.fw` / `ky.cwpm` settings to match.
- **Done when:** the example above sends as described, and turning the Farnsworth knob above the WPM knob turns
  Farnsworth off.

### Why it disconnected, in /DIAG (adapter)
- **What:** the adapter sometimes drops VBand and reconnects. /DIAG should say why, so a brownout can be told apart
  from a WiFi drop or a server disconnect without a USB cable. (The hardware side, bulk caps at the ESP32, is done.)
- **How:** at boot, read `esp_reset_reason()` and keep it (brownout, watchdog, power-on, software). Record WiFi
  disconnect reason codes (already printed by `DIAGNOSTICS_LOG`), WebSocket disconnects and the signal strength at
  each, with time since boot. Keep the last few in RTC memory or NVS so a reboot doesn't erase them. Show the
  summary in /DIAG on the keyer.
- **Done when:** after an unexplained reconnect, /DIAG shows whether the board reset (and why) or which connection
  dropped.

### The connecting screen never times out (adapter, keyer)
- **What:** while the adapter is connecting or reconnecting to VBand, its status screen on the keyer times out and
  disappears, so it looks like nothing is happening.
- **How:** status screens come with a display time (`ST,<ms>,...`). While connecting, send the screen with no
  timeout (or keep refreshing it), and update a line every few seconds with the attempt number or the elapsed time.
  Clear it when the channel is joined, when connecting stops, or when you leave the screen.
- **Done when:** the connecting screen stays up and visibly changes until it connects or gives up.

### Setting for the join announcement on the LED (adapter)
- **What:** after joining a channel, the LED blinks the channel's code in Morse. Make that a setting (on or off).
- **How:** the announcement is `startAnnounce()` in `led_indicator.cpp`. Add a boolean adapter setting (for example
  `vb.ann`, default on) and skip the announcement when it's off. The connection blinks and the keying LED stay.
- **Done when:** with the setting off, joining a channel doesn't blink the code; everything else on the LED is
  unchanged.

### VBand friends list (adapter, keyer)
- **What:** a list of friends' callsigns. The adapter notices when a friend is on VBand and can take you to their
  room.
- **How:**
  - A text setting for the list (`vb.friends`), with callsigns separated by a character the keyer can send (for
    example `/`).
  - The adapter already reads one channel's user list (`LU,<ch>`). Poll every channel's list, slowly (for example
    one channel every few seconds, and only while connected), and match names against the list the same way sender
    tags are found.
  - When a friend appears: a status screen and a line on the keyer saying who and which room.
  - A command to jump to the room a friend is in (`/FRIEND`, like `/BUSY`), and an optional startup mode that joins
    a friend's room if one is on (next to Lobby, Last and Custom).
- **Done when:** with a friend online, the keyer says where they are, `/FRIEND` joins that room, and the startup
  mode joins it at power-on.

## Features: need hardware work

### Amp drives the headphones (hardware)
- **What:** VBand audio is loud on the speaker but quiet in the headphones, even at full volume.
- **Why:** the headphones are driven passively: received audio reaches them through R9 22k, which into ~32 ohm
  headphones is about 7 times quieter than the Mega sidetone through its 4.7k. The speaker is fine because the amp
  makes up the difference. R9 can't simply be lowered: the ESP32 branch then drains the Mega's signal on the way to
  the amp.
- **How:** rewire so the amp drives the headphones too: HP_NODE straight to the amp's input; the amp's output to the
  jack's tip and ring; the speaker to the jack's switched contact (T′), so plugging in cuts it. No new parts; J3's
  three pins become amp out, T′ and sleeve. Drawn on the Audio sheet ("Amp drives headphones").
- **Done when:** VBand audio is about as loud in the headphones as on the speaker, the speaker still cuts out when
  headphones are plugged in, and the line out is unchanged.

### The ESP32 as the keyer's sidetone (hardware, adapter, keyer)
- **What:** the Mega's sidetone is a square wave from `tone()`, which clicks and can't fade. The ESP32 already plays
  received audio as a sine with a fade, and sounds better. Let it play your own sidetone too, with the Mega's kept
  as a fallback.
- **Why this needs hardware:** there's no firmware-only way to smooth the Mega's sidetone. The options looked at
  were K3NG's unfinished `FEATURE_SINEWAVE_SIDETONE_USING_TIMER_3` (needs an RC filter on pins 2/3/5, and its
  interrupt load could disturb keying timing) and an analog circuit to soften the edges (still a square wave).
- **How:**
  - Hardware: GPIO26 (DAC2) -> 1µF -> 2.2k onto the D52 line, so the main volume and the line out carry it. Drawn
    on the Audio sheet ("ESP32 sidetone").
  - Hardware: a sidetone key line, Mega D46 -> 10k / 22k divider -> ESP32 GPIO21 (D2), so the adapter knows when to
    sound. Also on the Audio sheet. D7 can't do this job: it only carries keying while you're on VBand, and it's
    silent for radio keying and command-mode beeps. (The other option, driving D7 in every mode and telling the
    adapter over the link which is meant, was turned down: it changes what D7 means, needs a link protocol bump, and
    still misses the beeps.)
  - Adapter: a second tone source on DAC2 following GPIO21 (an interrupt on each edge, as the key line does), using the existing sine table and fade, at the
    keyer's sidetone pitch (`st.hz`, sent over the link).
  - Keyer: a sidetone source setting (Mega / Adapter / Auto; Auto uses the adapter while the link is up and the
    Mega otherwise). When the adapter is the source, stop driving D52 (set it to an input) so it doesn't load the
    ESP32's signal, and drive D46 high whenever its sidetone would sound (keying on either line, and beeps).
- **Done when:** with the source on Adapter, your keying sounds as a clean faded tone in the headphones, speaker and
  line out; turning the adapter off falls back to the Mega under Auto.

### The keyer powers the ESP32 on (hardware, keyer)
- **What:** turn the adapter on from the keyer: a command when it's off, and a setting to power it on whenever the
  keyer starts.
- **How:**
  - Hardware: transistor T3 from Mega D44 onto the latch's gate node, in parallel with T1 (base through 10k, 1M to
    GND). Drawn on the ESP32 power latch sheet ("Power-on from the Mega").
  - Keyer: pulse D44 high for about 1.5 s; the ESP32 latches itself on and the link comes up. Add a "Power on" row
    or command that shows while the link is down (it fits where the VBand menu goes when the adapter is off), and a
    keyer setting to power the adapter on at start. Never hold D44 high, or the ESP32 can't turn itself off.
- **Done when:** the command and the start-up setting both power the adapter on, and /OFF and the button still
  turn it off.

## Hardware: finish the v0 build

Designed and drawn as part of the build, not wired yet.

- **TX keying output (J7):** D49 -> 2.2k -> T2 (2N2222A), emitter to GND, collector to the radio key jack's tip
  through J7. Done when the radio keys from the paddles with the keyer on radio (TX 1).
- **Straight key (J6):** jack tip -> J6 -> D34, with 10nF to GND. Then turn on `FEATURE_STRAIGHT_KEY` with
  `pin_straight_key = 34` in the keyer (its default, 52, is the sidetone). Done when a straight key on J6 keys the
  keyer, alongside the paddles.
- **Power switch (SW_PWR):** a toggle on the "To switch" connector, replacing the jumper.
- **Spare LED (D48):** it was the decoder's LED. Pick something for it to show (for example "on VBand" or "link
  up") and set it in the keyer.

## KiCad v1

- Draw the boards from `hardware/netlist.md`, including whichever proposals above are adopted.
- A power-path stage on the barrel input (an ideal diode or an automatic switch), so the barrel supply and the
  Mega's USB can never feed each other. Today's rule is to keep the barrel off while on USB.
- 10k / 20k link dividers (3.33V at the ESP32) instead of 10k / 22k (3.44V).
- Put the main volume's coupling cap ahead of its pot, as on the line out, so the pot doesn't carry D52's DC (which
  can make it crackle).
- Silkscreen: Stellaluna, with a moon and stars, and Stella's sweet face.
