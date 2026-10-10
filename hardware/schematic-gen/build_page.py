import os
import circuits

HERE = os.path.dirname(os.path.abspath(__file__))

def svg(name): return circuits.ALL[name]().svg()

SECTIONS = [
    ('power', 'Sheet 1', 'Power', 'HAT',
     'The barrel jack feeds one +5V rail through the fuse. Everything runs from that rail except the ESP32, which gets its 5V from the latch.'),
    ('latch', 'Sheet 2', 'ESP32 power latch', 'LB · HAT',
     'A P-channel MOSFET switches the ESP32’s 5V. The button turns it on, the ESP32 holds it on through T1, and the same button doubles as the channel button.'),
    ('link', 'Sheet 3', 'Mega ↔ ESP32 link', 'HAT',
     'Serial link at 38400 baud plus the VBand key line. The Mega’s 5V outputs reach the ESP32 through dividers.'),
    ('audio', 'Sheet 4', 'Audio', 'HAT · FP',
     'The Mega sidetone feeds the main volume (headphones and speaker) and the line out. Received VBand audio from the ESP32 joins at the headphone point only.'),
    ('inputs', 'Sheet 5', 'Paddle and speed pots', 'HAT · LB',
     'Paddle on D30 (dit, tip) and D32 (dah, ring). The speed pots are on the latch board; their 10nF caps sit at the Mega pins.'),
    ('buttons', 'Sheet 6', 'Button ladder', 'FP',
     'Eight buttons on one analog pin. The command button sits directly on A1; each one after it is 1k further down the chain.'),
    ('leds', 'Sheet 7', 'LEDs and OLED', 'FP · HAT',
     'Status LEDs driven straight from pins through their resistors, and the I2C OLED.'),
    ('txkey', 'Sheet 8', 'TX keying and straight key', 'HAT',
     'The transistor that keys the radio from D49, and the straight key jack. Both are part of the build; they just aren’t wired up yet.'),
]

J_FP = [(1, 'GND'), (2, 'Mega D52 sidetone → VR1 leg'), (3, 'Mega D50 command mode LED'), (4, 'VR1 wiper (main out) → C4 → R3 → HP_NODE'),
        (7, 'ESP32 GPIO15 status LED'), (11, 'Mega D48 spare LED'), (12, 'VR2 wiper → J4 line out tip'),
        (13, 'Sidetone in: D52 → R3 → C4 → VR2 leg'), (14, 'Mega D49 TX LED'), (18, 'Button ladder → Mega A1'),
        (20, 'ESP32 GPIO25 → VR3 leg'), (21, 'VR3 wiper → C4 → R9 → HP_NODE'), (22, 'OLED SCL (Mega D21)'),
        (23, 'OLED SDA (Mega D20)'), (24, '+5V: OLED VCC, ladder R1')]
J_LB = [(2, '+5V_LATCHED out → JP1 → ESP32 5V'), (3, '+5V in → M1 source (R8 gate pull-up)'), (4, 'LATCH (ESP32 GPIO4)'),
        (8, '+5V → Farnsworth pot'), (9, '+5V → WPM pot'), (13, 'Farnsworth wiper → Mega A0'), (14, 'WPM wiper → Mega A2'),
        (15, 'ESP BTN (ESP32 GPIO17)'), (16, 'GND')]

BOM = [  # code, value, as built, proposed, where
    ('R1', '10k', 6, 8, 'link (3), latch base, TX LED, ladder pull-up; + T3 base, sidetone key divider'),
    ('R2', '1k', 7, 7, 'button ladder'),
    ('R3', '4.7k', 3, 3, 'main and line-out audio, spare LED'),
    ('R4', '220Ω', 2, 2, 'command LED, ESP32 LED'),
    ('R5', '2.2k', 1, 2, 'TX keying base; + GPIO26 sidetone'),
    ('R8', '1M', 2, 3, 'latch gate pull-up and T1 base; + T3 base'),
    ('R9', '22k', 3, 4, 'link dividers (2), received audio; + sidetone key divider'),
    ('C1', '100nF ceramic', 2, 2, 'amp module supply, ESP32 5V'),
    ('C2', '10nF ceramic', 5, 5, 'paddle lines, straight key, speed pot wipers'),
    ('C4', '3.3µF electrolytic', 3, 3, 'main, line out, received audio coupling'),
    ('C5', '1µF ceramic', 1, 2, 'amp module supply; + GPIO26 coupling'),
    ('C6', '470µF electrolytic', 1, 1, 'ESP32 5V bulk'),
    ('VR', '10k log (A10K)', 3, 3, 'main, line out, received volume'),
    ('VR', '10k linear', 2, 2, 'WPM, Farnsworth'),
    ('T', '2N2222A', 2, 3, 'T1 latch hold, T2 TX keying; + T3 power-on'),
    ('M1', 'IRF5305', 1, 1, 'latch switch'),
    ('D', '1N4148', 2, 2, 'D1, D2 latch'),
    ('F1', '2A fuse', 1, 1, 'after the barrel jack'),
    ('LED', '', 4, 4, 'command, ESP32, TX, spare'),
]

CHANGES = [
    ('Audio', 'ESP32 sidetone: add GPIO26 (DAC2) → C5 1µF → R5 2.2k onto the D52 net for an own-keying sidetone from the ESP32, and a sidetone key line (Mega D46 → 10k / 22k divider → ESP32 GPIO21) that tells it when to sound. Firmware setting st.src (Mega / Adapter / Auto).'),
    ('Audio', 'Amp drives headphones: HP_NODE goes straight to the amp input, the amp output drives the jack’s tip and ring, and the speaker moves to the jack’s switched contact (T′). Makes VBand audio as loud in the headphones as on the speaker; no new parts.'),
    ('Latch', 'Add T3 with R1 10k from Mega D44 and R8 1M base to GND, collector on the gate node: the keyer can power the ESP32 on.'),
    ('KiCad v1', 'Power-path stage on the barrel input, so the barrel supply and the Mega’s USB can never feed each other.'),
    ('KiCad v1', 'Link dividers 10k / 20k (3.33V) instead of 10k / 22k (3.44V).'),
]

def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def variants(sid):
    """[(combo, svg name)] for a sheet: as built first, then each proposal, then combinations."""
    fn, props = circuits.SHEETS[sid]
    return [(c, circuits.variant_name(sid, c)) for c in circuits.combos(props)]

def page():
    figs = []
    for sid, sheet, title, boards, desc in SECTIONS:
        props = circuits.SHEETS[sid][1]
        body = ''.join(f'<div class="plate" data-combo="{"+".join(c)}"{"" if not c else " hidden"}>{svg(n)}</div>'
                       for c, n in variants(sid))
        if props:
            tag = ('<div class="props" role="group" aria-label="Proposed changes on this sheet">'
                   '<span class="props-lab">Show proposed:</span>' +
                   ''.join(f'<button type="button" data-k="{k}" aria-pressed="false">{esc(l)}</button>' for k, l in props) +
                   '</div>')
        else:
            tag = '<span class="chip same">no changes</span>'
        figs.append(f'''<section class="sheet" id="{sid}">
  <header class="tb">
    <span class="tb-sheet">{sheet}</span><h2>{title}</h2><span class="tb-boards">{boards}</span>{tag}
  </header>
  <p class="desc">{desc}</p>
  <div class="scroll">{body}</div>
</section>''')
    fp = ''.join(f'<tr><td class="num">{n}</td><td>{esc(s)}</td></tr>' for n, s in J_FP)
    lb = ''.join(f'<tr><td class="num">{n}</td><td>{esc(s)}</td></tr>' for n, s in J_LB)
    bom = ''.join(f'<tr><td class="code">{c}</td><td>{esc(v)}</td><td class="num">{a}</td><td class="num{" diff" if a != p else ""}">{p}</td><td>{esc(w)}</td></tr>' for c, v, a, p, w in BOM)
    ch = ''.join(f'<li><span class="where">{esc(w)}</span><span>{esc(t)}</span></li>' for w, t in CHANGES)
    return TEMPLATE.replace('{{FIGS}}', '\n'.join(figs)).replace('{{FP}}', fp).replace('{{LB}}', lb).replace('{{BOM}}', bom).replace('{{CHANGES}}', ch)

TEMPLATE = open(os.path.join(HERE, 'page_template.html')).read()

def markdown():
    """hardware/schematics.md plus one SVG per sheet in hardware/schematics/, for viewing on GitHub."""
    from sym import standalone
    d = os.path.join(HERE, '..', 'schematics')
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        if f.endswith('.svg'): os.remove(os.path.join(d, f))
    md = ['# Stellaluna schematics', '',
          'One sheet per circuit, drawn from [netlist.md](netlist.md). Where changes are proposed, the as-built sheet '
          'comes first, then each proposal on its own, then proposals combined; new or changed parts are pink. The same '
          'sheets, with a toggle for each proposal, header pinouts and a parts list, are in [schematics.html](schematics.html) '
          '(download it and open it in a browser).', '',
          'Designators use the value codes (R1 = 10k, C4 = 3.3µF, ...), so a code appears wherever that value is used.', '',
          '## Proposed changes', '']
    md += [f'- **{w}:** {t}' for w, t in CHANGES]
    md.append('')
    for sid, sheet, title, boards, desc in SECTIONS:
        props = dict(circuits.SHEETS[sid][1])
        md += [f'## {sheet}: {title}', '', f'*{boards}.* {desc}', '']
        for c, name in variants(sid):
            open(os.path.join(d, f'{name}.svg'), 'w').write(standalone(circuits.ALL[name]()))
            cap = None if not props else ('As built' if not c else 'Proposed: ' + ' + '.join(props[k] for k in c))
            if cap: md += [f'**{cap}**', '']
            md += [f'![{title}{" (" + cap + ")" if cap else ""}](schematics/{name}.svg)', '']
    open(os.path.join(HERE, '..', 'schematics.md'), 'w').write('\n'.join(md))

if __name__ == '__main__':
    markdown()
    out = page()
    open(os.path.join(HERE, '..', 'schematics.html'), 'w').write(out)
    print(len(out))
