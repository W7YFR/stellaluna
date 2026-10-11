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

None open.

## Keyer features (firmware only)

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

### Button remapping (keyer)
- **What:** choose which job each physical button does: for example, the first button on the panel acts as
  memory 3 and the third acts as the command button, so the buttons can be laid out to suit without rewiring the
  resistor ladder.
- **How:** the ladder on A1 is decoded into button numbers in `initialize_analog_button_array()` (a low and high
  analog limit per button), and everything downstream (`analogbuttonread()`, `check_buttons()`, memories, extra
  buttons, command mode) works on those numbers. Remap at that one point: give logical button N the analog window
  of physical button `map[N]`, so nothing else changes. Start with a compile-time table behind an option (for
  example `OPTION_BUTTON_MAP` with `button_map[] = {...}` in the settings files, one entry per button, identity by
  default), and check it's a permutation at boot. A menu setting could follow (saved in the spare EEPROM bytes
  after the configuration), but every row of the table is a setting, so it needs a good menu design first.
- **Done when:** with a map set, each physical button does the job it's mapped to, in normal and command mode,
  including holds and the extra button; with no map, nothing changes.

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

## VBand features (firmware only)

The adapter, and its side of the keyer.

### Notice a stalled VBand connection sooner (adapter)
- **What:** a VBand drop seen on 2026-10-10 (`/DIAG`: `ws1 wifi0`, no reboot) came after a near-5 s gap in
  someone's sending: the connection seems to stall before it's closed, and nothing on our side notices until the
  server or the network closes it.
- **How:** first collect a few drops with `/LAST` and the logged event list (each VBand drop keeps how long the server
  had been silent before it). If they're stalls, turn on the WebSocket library's heartbeat
  (`ws.enableHeartbeat(ping interval, pong timeout, missed pongs)`), so a dead connection is dropped and reconnected
  within a few seconds; check the VBand server answers pings first, and don't make it so tight that a slow moment
  reconnects needlessly. If they're abrupt closes with no silence before them, it's the server's doing, and there's
  nothing to change here.
- **Done when:** the cause of the drops is known, and, if they're stalls, one is reconnected within a few seconds of
  the server going silent.

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

## Features that need hardware work

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
