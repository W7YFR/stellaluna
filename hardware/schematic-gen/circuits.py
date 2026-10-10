from sym import Sheet

def latch(on=frozenset()):
    proposed = 'poweron' in on
    s = Sheet()
    # +5V rail
    s.port(150, 40, '+5V (J_LB 3)', 'left')
    s.wire((150, 40), (308, 40)); s.dot(220, 40)
    m = s.pmos(300, 120, 'M1 IRF5305')
    s.wire((308, 40), m['S'])
    s.res((220, 40), (220, 120), 'R8 1M', side='left')
    s.dot(220, 120); s.wire((220, 120), m['G'])
    # drain -> latched 5V, bulk caps at the ESP32
    s.wire(m['D'], (308, 170), (760, 170))
    s.dot(600, 170); s.cap((600, 170), (600, 226), 'C6\n470µF', polar=True); s.ground(600, 226)
    s.dot(680, 170); s.cap((680, 170), (680, 226), 'C1\n100nF'); s.ground(680, 226)
    s.port(760, 170, '+5V_LATCHED (J_LB 2)\n→ JP1 → ESP32 5V', 'right')
    s.note(590, 270, 'C6 and C1 sit at the\nESP32 5V pins (HAT)')
    # T1 hold
    s.wire((220, 120), (220, 198))
    t = s.npn(212, 224, 'T1\n2N2222A')
    s.ground(*t['E'])
    s.wire(t['B'], (160, 224)); s.dot(160, 224)
    s.res((160, 224), (160, 290), 'R8 1M', side='left'); s.ground(160, 290)
    s.res((160, 224), (70, 224), 'R1 10k')
    s.port(70, 224, 'LATCH\nESP32 GPIO4 (J_LB 4)', 'left')
    # D1 / button / D2
    s.diode((220, 120), (150, 120), 'D1 1N4148')
    s.dot(150, 120)
    s.button((150, 120), (150, 176), 'SW9\npower /\nchannel', side='left'); s.ground(150, 176)
    s.diode((60, 120), (150, 120), 'D2 1N4148', side='up')
    s.port(60, 120, 'ESP BTN\nESP32 GPIO17 (J_LB 15)', 'left')
    s.note(-90, 350, 'Pressing SW9 pulls the gate low through D1 (power on) and GPIO17 low through D2 (channel button).')
    s.note(-90, 366, 'T1 holds the gate low once the ESP32 drives LATCH high.')
    if proposed:
        s.cls = 'n'
        s.dot(220, 190, cls='n')
        s.wire((220, 190), (324, 190), (324, 224))
        t2 = s.npn(332, 250, '', mirror=True)
        s.text(372, 222, 'T3 2N2222A (new)')
        s.ground(*t2['E'])
        s.wire(t2['B'], (400, 250)); s.dot(400, 250)
        s.res((400, 250), (400, 310), 'R8 1M'); s.ground(400, 310)
        s.res((400, 250), (500, 250), 'R1 10k', side='down')
        s.port(500, 250, 'Mega D44 (new wire)', 'right')
        s.note(-90, 382, 'New: the keyer pulses D44 ~1.5 s to power the ESP32 on, the same as pressing SW9 but without a channel press.')
        s.cls = 'w'
    return s

def link():
    s = Sheet()
    s.port(80, 40, 'Mega D16 (TX2)', 'left')
    s.res((80, 40), (180, 40), 'R1 10k')
    s.wire((180, 40), (300, 40)); s.dot(220, 40)
    s.res((220, 40), (220, 100), 'R9 22k'); s.ground(220, 100)
    s.port(300, 40, 'ESP32 GPIO19 (link RX)', 'right')

    s.port(80, 160, 'ESP32 GPIO18 (link TX)', 'left')
    s.res((80, 160), (180, 160), 'R1 10k')
    s.wire((180, 160), (300, 160))
    s.port(300, 160, 'Mega D17 (RX2)', 'right')

    s.port(80, 240, 'Mega D7 (VBand key, TX2 line)', 'left')
    s.res((80, 240), (180, 240), 'R1 10k')
    s.wire((180, 240), (300, 240)); s.dot(220, 240)
    s.res((220, 240), (220, 300), 'R9 22k'); s.ground(220, 300)
    s.port(300, 240, 'ESP32 GPIO22 (key in)', 'right')
    s.note(-60, 350, 'Dividers: 5V × 22k / 32k = 3.44V at the ESP32 (max 3.6V). KiCad: 10k / 20k.')
    return s

def audio(on=frozenset()):
    st, hp = 'st' in on, 'hp' in on
    s = Sheet()
    # Mega sidetone bus
    s.port(60, 80, 'Mega D52\n(J_FP 2)', 'left')
    s.wire((60, 80), (240, 80)); s.dot(140, 80)
    # main volume
    w1 = s.pot((240, 80), (240, 160), 'VR1 main\n10k log (FP)', side='left')
    s.ground(240, 160)
    s.wire(w1, (290, 120))
    s.cap((290, 120), (350, 120), 'C4 3.3µF', polar=True)
    s.res((350, 120), (440, 120), 'R3 4.7k')
    s.wire((440, 120), (600, 120)); s.dot(600, 120)
    s.note(256, 105, 'J_FP 4')
    # line out
    s.wire((140, 80), (140, 220))
    s.res((140, 220), (220, 220), 'R3 4.7k', side='down')
    s.cap((220, 220), (290, 220), 'C4 3.3µF', side='down', polar=True)
    s.wire((290, 220), (340, 220))
    s.note(296, 212, 'J_FP 13')
    w2 = s.pot((340, 220), (340, 300), 'VR2 line out\n10k log (FP)', side='left')
    s.ground(340, 300)
    s.wire(w2, (420, 260))
    s.port(420, 260, 'J4 line out tip\n(2-pin JST, J_FP 12)', 'right')
    s.note(420, 296, 'J4 sleeve → GND')
    # ESP received audio
    s.port(60, 380, 'ESP32 GPIO25\nDAC1 (J_FP 20)', 'left')
    s.wire((60, 380), (240, 380))
    w3 = s.pot((240, 380), (240, 460), 'VR3 received\n10k log (FP)', side='left')
    s.ground(240, 460)
    s.wire(w3, (290, 420))
    s.note(256, 405, 'J_FP 21')
    s.cap((290, 420), (350, 420), 'C4 3.3µF', side='down', polar=True)
    s.res((350, 420), (440, 420), 'R9 22k', side='down')
    s.wire((440, 420), (600, 420), (600, 120))
    s.text(560, 145, 'HP_NODE', 'middle')
    if not hp:
        # headphone jack: headphones driven passively from HP_NODE; T' feeds the amp with no plug in
        j3 = s.box(662, 100, 130, 60, 'J3 headphones (3-pin JST)\nT, R, R′ tied at the jack', left=['T, R, R′', 'sleeve'], right=["T′ (no plug)"], pitch=24)
        s.wire((600, 120), j3['T, R, R′'])
        s.wire(j3['sleeve'], (636, j3['sleeve'][1]), (636, 160)); s.ground(636, 160)
    u3 = s.box(860, 80, 110, 110, 'U3 LM386 module (gain 20)', left=['IN', 'VCC', 'GND'], right=['OUT+', 'OUT−'], pitch=26, top=22)
    if not hp:
        s.wire(j3["T′ (no plug)"], (820, j3["T′ (no plug)"][1]), (820, u3['IN'][1]), u3['IN'])
    s.wire(u3['GND'], (836, u3['GND'][1]), (836, 150 + 52)); s.ground(836, 202)
    s.wire(u3['VCC'], (800, u3['VCC'][1]), (800, 250))
    s.rail(800, 250 + 0, '')
    s.port(800, 250, '+5V', 'down')
    s.dot(800, 220); s.wire((800, 220), (680, 220)); s.dot(740, 220)
    s.cap((740, 220), (740, 276), 'C5\n1µF', side='left'); s.ground(740, 276)
    s.cap((680, 220), (680, 276), 'C1\n100nF', side='left'); s.ground(680, 276)
    if not hp:
        s.wire(u3['OUT+'], (1010, u3['OUT+'][1]))
        s.wire(u3['OUT−'], (1000, u3['OUT−'][1]), (1000, u3['OUT+'][1] + 20), (1010, u3['OUT+'][1] + 20))
        s.speaker(1010, u3['OUT+'][1])
        s.text(1030, u3['OUT+'][1] + 52, 'J5 speaker\n(2-pin JST)', 'middle')
        s.note(600, 470, 'Plugging in headphones disconnects T′, so the amp and speaker go quiet.')
    else:
        # the amp drives the headphones; the jack's switch cuts the speaker
        s.cls = 'n'
        s.wire((600, 120), (820, 120), (820, u3['IN'][1]), u3['IN'])
        j3 = s.box(1070, 86, 150, 60, 'J3 headphones (3-pin JST)\nT and R tied at the jack', left=['T, R (both ears)', 'sleeve'], right=["T′ (no plug)"], pitch=24, top=16)
        s.wire(u3['OUT+'], j3['T, R (both ears)'])
        s.wire(j3['sleeve'], (1036, j3['sleeve'][1]), (1036, 166)); s.ground(1036, 166)
        tp = j3["T′ (no plug)"]
        sx = tp[0] + 20
        s.wire(tp, (sx, tp[1]))
        s.speaker(sx, tp[1])
        s.wire((sx, tp[1] + 20), (sx - 10, tp[1] + 20), (sx - 10, 230), (994, 230), (994, u3['OUT−'][1]), u3['OUT−'])
        s.text(sx + 22, tp[1] + 52, 'J5 speaker\n(2-pin JST)', 'middle')
        s.note(600, 470, 'New: the amp drives the headphones too. Plugging them in opens T′, which cuts the speaker.')
        s.note(600, 486, 'J3 carries amp out (to T and R), T′ (to the speaker) and sleeve. Start with the knobs low: it’s much louder.')
        s.cls = 'w'
    if st:
        s.cls = 'n'
        s.port(60, 20, 'ESP32 GPIO26\nDAC2 (new)', 'left')
        s.cap((60, 20), (110, 20), 'C5 1µF')
        s.res((110, 20), (190, 20), 'R5 2.2k')
        s.wire((190, 20), (200, 20), (200, 80)); s.dot(200, 80)
        # sidetone key line: tells the ESP32 when to sound (D7 only carries VBand keying)
        s.port(60, -90, 'Mega D46\nsidetone key (new)', 'left')
        s.res((60, -90), (150, -90), 'R1 10k')
        s.wire((150, -90), (300, -90)); s.dot(200, -90)
        s.res((200, -90), (200, -36), 'R9 22k'); s.ground(200, -36)
        s.port(300, -90, 'ESP32 GPIO21 (D2)\nsidetone key in', 'right')
        s.note(-60, 540, 'New: own-keying sidetone from the ESP32 joins the D52 net, so VR1 and the line out carry it too.')
        s.note(-60, 556, 'Firmware tri-states whichever source isn’t selected (st.src = Mega / Adapter / Auto). No resistor on D52.')
        s.note(-60, 572, 'The ESP32 sounds while D46 is high (radio keying, VBand keying and beeps); D7 still carries only VBand keying.')
        s.cls = 'w'
    return s

def power(on=frozenset()):
    proposed = 'path' in on
    s = Sheet()
    s.port(40, 60, 'J1 5V DC\nbarrel +', 'left')
    s.fuse((40, 60), (120, 60), 'F1 2A')
    s.switch((120, 60), (200, 60), 'SW_PWR toggle\n(2-pin JST; jumpered\nuntil wired)')
    if proposed:
        s.cls = 'n'
        s.box(214, 44, 100, 32, 'power path (KiCad v1)', top=16)
        s.wire((200, 60), (214, 60)); s.wire((314, 60), (340, 60)); s.cls = 'w'
        x0 = 340
    else:
        x0 = 200
    s.wire((x0, 60), (x0 + 60, 60), (x0 + 60, 260))
    s.text(x0 + 10, 50, '+5V')
    loads = ['Mega 5V pin (not VIN)', 'U3 LM386 module VCC', 'J_FP 24 → OLED VCC, button ladder R1',
             'J_LB 3 → M1 source (ESP32 latch)', 'J_LB 9 → WPM pot', 'J_LB 8 → Farnsworth pot']
    for i, l in enumerate(loads):
        y = 90 + i * 34
        s.dot(x0 + 60, y); s.wire((x0 + 60, y), (x0 + 110, y)); s.port(x0 + 110, y, l, 'right')
    s.port(40, 130, 'J1 −', 'left'); s.wire((40, 130), (80, 130)); s.ground(80, 130)
    s.note(-60, 320, 'One ground for everything. The ESP32 is the only load not on +5V: it runs from the latch (+5V_LATCHED via JP1).')
    s.note(-60, 336, 'Rule for v0: barrel off while the Mega is on USB (USB 5V and +5V would be tied through the Mega).')
    if proposed:
        s.note(-60, 352, 'KiCad v1: an ideal-diode / power-path stage so the barrel supply and USB can never feed each other.')
    return s

def inputs():
    s = Sheet()
    j2 = s.box(40, 30, 60, 76, 'J2 paddle\n(3-pin JST to TRS jack)', right=['tip', 'ring', 'sleeve'], pitch=22)
    s.wire(j2['tip'], (300, j2['tip'][1])); s.dot(250, j2['tip'][1])
    s.port(300, j2['tip'][1], 'Mega D30 (dit)', 'right')
    s.wire(j2['ring'], (300, j2['ring'][1])); s.dot(190, j2['ring'][1])
    s.port(300, j2['ring'][1], 'Mega D32 (dah)', 'right')
    s.cap((250, j2['tip'][1]), (250, 150), 'C2\n10nF'); s.ground(250, 150)
    s.cap((190, j2['ring'][1]), (190, 150), 'C2\n10nF'); s.ground(190, 150)
    s.wire(j2['sleeve'], (140, j2['sleeve'][1])); s.ground(140, j2['sleeve'][1])
    # speed pots
    for i, (name, jl, jw, pin) in enumerate((('VR4 WPM', 'J_LB 9', 'J_LB 14', 'Mega A2'), ('VR5 Farnsworth', 'J_LB 8', 'J_LB 13', 'Mega A0'))):
        x = 480 + i * 270
        s.rail(x, 40, '+5V'); s.text(x + 8, 60, jl)
        w = s.pot((x, 40), (x, 120), f'{name}\n10k linear (LB)', side='left')
        s.ground(x, 120)
        s.wire(w, (x + 120, w[1])); s.dot(x + 70, w[1])
        s.cap((x + 70, w[1]), (x + 70, 140), 'C2\n10nF'); s.ground(x + 70, 140)
        s.port(x + 120, w[1], f'{pin}\n({jw})', 'right')
    s.note(480, 200, 'The C2s sit at the Mega pins on the HAT.')
    return s

def buttons():
    s = Sheet()
    s.rail(80, 30, '+5V (J_FP 24)')
    s.res((80, 30), (80, 100), 'R1 10k', side='left')
    s.port(20, 100, 'Mega A1\n(J_FP 18)', 'left'); s.wire((20, 100), (80, 100))
    names = ['SW1\ncommand', 'SW2\nmemory 1', 'SW3\nmemory 2', 'SW4\nmemory 3', 'SW5\nmemory 4', 'SW6\nmemory 5', 'SW7\nmemory 6', 'SW8\nextra']
    for i, n in enumerate(names):
        x = 80 + i * 100
        s.dot(x, 100)
        if i < 7: s.res((x, 100), (x + 100, 100), 'R2 1k')
        s.button((x, 100), (x, 160), n, side='right' if i < 7 else 'right'); s.ground(x, 160)
    s.note(20, 220, 'K3NG analog ladder (analog_buttons_r1 = 10k, analog_buttons_r2 = 1k). All on the front panel.')
    return s

def leds():
    s = Sheet()
    rows = [('Mega D50 · command mode (J_FP 3)', 'led-res', 'R4 220'),
            ('ESP32 GPIO15 · status (J_FP 7)', 'led-res', 'R4 220'),
            ('Mega D49 · TX (J_FP 14)', 'res-led', 'R1 1k'),
            ('Mega D48 · spare (J_FP 11)', 'led-res', 'R3 4.7k')]
    for i, (lab, order, r) in enumerate(rows):
        y = 40 + i * 60
        s.port(60, y, lab, 'left')
        if order == 'led-res':
            s.diode((60, y), (130, y), 'LED', side='down', led=True); s.res((130, y), (210, y), r)
        else:
            s.res((60, y), (140, y), r); s.diode((140, y), (210, y), 'LED', side='down', led=True)
        s.wire((210, y), (230, y)); s.ground(230, y)
    s.note(-200, 290, 'LEDs on the front panel; R4 for D50 sits on the HAT.')
    # OLED
    u4 = s.box(460, 20, 110, 104, 'U4 SSD1306 OLED (FP)', left=['VCC', 'GND', 'SCL', 'SDA'], pitch=22)
    for n, lab in (('VCC', '+5V (J_FP 24)'), ('SCL', 'Mega D21 (J_FP 22)'), ('SDA', 'Mega D20 (J_FP 23)')):
        s.wire(u4[n], (420, u4[n][1])); s.port(420, u4[n][1], lab, 'left')
    s.wire(u4['GND'], (436, u4['GND'][1]), (436, 150)); s.ground(436, 150)
    return s

def txkey():
    s = Sheet()
    s.port(40, 80, 'Mega D49 (tx_key_line_1)', 'left')
    s.res((40, 80), (130, 80), 'R5 2.2k')
    t = s.npn(156, 80, 'T2 2N2222A')
    s.wire((130, 80), t['B'])
    s.ground(*t['E'])
    j7 = s.box(330, 10, 70, 54, 'J7 radio key\n(2-pin JST to jack)', left=['tip', 'sleeve'], pitch=22)
    s.wire(t['C'], (164, 30), j7['tip'])
    s.wire(j7['sleeve'], (300, j7['sleeve'][1])); s.ground(300, j7['sleeve'][1])
    s.note(-120, 160, 'The TX LED hangs off D49 itself (LEDs and OLED sheet), not the radio line.')
    # straight key
    j6 = s.box(-120, 210, 60, 54, 'J6 straight key\n(2-pin JST to TRS jack)', right=['tip', 'sleeve'], pitch=22)
    s.wire(j6['tip'], (110, j6['tip'][1])); s.dot(40, j6['tip'][1])
    s.cap((40, j6['tip'][1]), (40, 290), 'C2\n10nF'); s.ground(40, 290)
    s.port(110, j6['tip'][1], 'Mega D34', 'right')
    s.wire(j6['sleeve'], (0, j6['sleeve'][1])); s.ground(0, j6['sleeve'][1])
    s.note(-120, 330, 'Straight key: not enabled in the firmware yet. When wired, turn on FEATURE_STRAIGHT_KEY with pin_straight_key = 34.')
    return s

# name -> (draw function taking a set of proposal keys, proposals: [(key, label)])
SHEETS = {
    'power': (power, [('path', 'Power path')]),
    'latch': (latch, [('poweron', 'Power-on from the Mega')]),
    'link': (lambda on=frozenset(): link(), []),
    'audio': (audio, [('st', 'ESP32 sidetone'), ('hp', 'Amp drives headphones')]),
    'inputs': (lambda on=frozenset(): inputs(), []),
    'buttons': (lambda on=frozenset(): buttons(), []),
    'leds': (lambda on=frozenset(): leds(), []),
    'txkey': (lambda on=frozenset(): txkey(), []),
}

def combos(props):
    """Every subset of a sheet's proposal keys, as sorted tuples: (), ('hp',), ('hp', 'st'), ..."""
    keys = sorted(k for k, _ in props)
    out = [()]
    for k in keys: out += [c + (k,) for c in out]
    return sorted(out, key=lambda c: (len(c), c))

def variant_name(sheet, combo): return '+'.join((sheet,) + tuple(combo))

ALL = {variant_name(n, c): (lambda f=f, c=c: f(frozenset(c))) for n, (f, props) in SHEETS.items() for c in combos(props)}

if __name__ == '__main__':
    import os, sys, subprocess
    from sym import preview
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
    os.makedirs(out, exist_ok=True)
    names = sys.argv[1:] or list(ALL)
    for n in names:
        svg = os.path.join(out, f'{n}.svg')
        preview(ALL[n](), svg)
        subprocess.run(['rsvg-convert', '-z', '1.5', svg, '-o', os.path.join(out, f'{n}.png')], check=True)
    print('ok', names)
