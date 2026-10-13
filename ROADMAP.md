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

### Choose the USB port's mode: CLI or Winkey (keyer)
- **What:** with `FEATURE_WINKEY_EMULATION` built in, the USB port is either the CLI (115200 baud, text: `\S`,
  `\$`, the `ESP>` log) or Winkey emulation (1200 baud, the WinKeyer's binary protocol, for logging programs), never
  both. K3NG only chooses at power-on: the default comes from `OPTION_PRIMARY_SERIAL_PORT_DEFAULT_WINKEY_EMULATION`
  and holding the command button gives the other. Make it a saved setting instead, so Winkey is something you turn
  on when you want it rather than a power-on default.
- **How:** a "USB port" setting (CLI / Winkey) in the menu and as `ky.usb` (`/KY USB WINKEY`, `\$ ky.usb winkey`),
  only in builds with both `FEATURE_WINKEY_EMULATION` and `FEATURE_COMMAND_LINE_INTERFACE`, saved in the spare
  EEPROM bytes after the configuration (`SETTINGS_EXTRAS_ADDRESS`). Changing it switches the port straight away:
  end it, set `primary_serial_port_mode`, and begin it again at the mode's baud rate (the Winkey code already ends
  and reopens the port for a host). At power-on the saved setting decides; the option is only the default before
  anything is saved, and the command button at power-on still gives the other mode for that session, as a way back
  without the display. Leaving Winkey mode should close any host session cleanly.
- **Done when:** the menu or the CLI switches the port between CLI and Winkey without a power cycle, the choice
  survives one, and builds without Winkey emulation don't show the setting.

### Winkey hosts with the Farnsworth effective speed option (keyer)
- **What:** with `OPTION_FARNSWORTH_SETS_EFFECTIVE_SPEED` (on in `w7yfr`), the keyer's speed is the character speed
  and its Farnsworth setting the effective speed. A Winkey host (N1MM, Win-Test and the like, over
  `FEATURE_WINKEY_EMULATION`) still means K3NG's and the K1EL WinKeyer's way: its speed is the overall speed and its
  Farnsworth speed a faster character speed. So "speed 10, Farnsworth 25" from a host (characters at 25, overall 10)
  reads as Farnsworth off and sends everything at 10. Winkey emulation isn't in the `w7yfr` build today.
- **How:** a small translation layer at the Winkey edge, only with the option: two helpers and edits where Winkey
  commands come in and reports go out, probably 50 to 80 lines. Keep the host's view of the two speeds and map it
  onto the keyer's: Farnsworth on (host Farnsworth above host speed) means speed = host Farnsworth and Farnsworth =
  host speed; otherwise speed = host speed and Farnsworth off. Incoming: the speed command
  (`winkey_unbuffered_speed_command()`), the Farnsworth command (`winkey_farnsworth_command()`), HSCW and loading
  settings (`winkey_load_settings_command()`). Outgoing, map back: the speed pot reports (`(wpm - pot_wpm_low_value)
  | 128`, in a few places) and the settings dump (which writes `wpm_farnsworth` and the speed). Decided: the speed
  pot keeps meaning the character speed while a host is connected, and is reported to the host as its Farnsworth
  (character) speed when Farnsworth is on.
- **Testing:** needs `FEATURE_WINKEY_EMULATION` in a build, which puts the USB port in Winkey mode (1200 baud, the
  binary protocol; no CLI or `ESP>` log) at power-on; the command button held at power-on gives the CLI instead
  (with `OPTION_PRIMARY_SERIAL_PORT_DEFAULT_WINKEY_EMULATION`, set in `w7yfr`; without it, the other way round).
  Test with a logging program, or a short Python script that sends Winkey commands and reads the replies.
- **Done when:** with the option on, a host's speed and Farnsworth settings send as they would on a K1EL WinKeyer,
  the host shows the right speed when the pot moves, and nothing changes without the option.

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
