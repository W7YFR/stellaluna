"""Tiny schematic DSL: explicit coordinates, SVG out, colors via CSS classes (theme-aware)."""
import math

class Sheet:
    def __init__(self):
        self.parts = []
        self.minx = self.miny = 1e9
        self.maxx = self.maxy = -1e9
        self.cls = 'w'  # current class: 'w' existing, 'n' new, 'x' removed

    def _bb(self, x, y):
        self.minx = min(self.minx, x); self.maxx = max(self.maxx, x)
        self.miny = min(self.miny, y); self.maxy = max(self.maxy, y)

    def raw(self, s): self.parts.append(s)

    # ---- primitives
    def line(self, *pts, cls=None):
        for x, y in pts: self._bb(x, y)
        p = ' '.join(f'{x},{y}' for x, y in pts)
        self.raw(f'<polyline class="{cls or self.cls}" points="{p}"/>')

    def wire(self, *pts, cls=None): self.line(*pts, cls=cls)

    def dot(self, x, y, cls=None):
        self._bb(x, y)
        self.raw(f'<circle class="{cls or self.cls} f" cx="{x}" cy="{y}" r="3"/>')

    def text(self, x, y, s, anchor='start', cls='t', size=None):
        lines = s.split('\n')
        w = max(len(l) for l in lines) * 6.4
        h = len(lines) * 13
        x0 = x if anchor == 'start' else (x - w if anchor == 'end' else x - w / 2)
        self._bb(x0, y - 11); self._bb(x0 + w, y - 11 + h)
        sz = f' font-size="{size}"' if size else ''
        tc = cls if self.cls == 'w' or cls != 't' else f't {self.cls}t'
        out = f'<text class="{tc}" x="{x}" y="{y}" text-anchor="{anchor}"{sz}>'
        for i, l in enumerate(lines):
            out += f'<tspan x="{x}" dy="{0 if i == 0 else 13}">{esc(l)}</tspan>'
        self.raw(out + '</text>')

    def port(self, x, y, label, side='left'):
        """Open circle terminal with a label on `side` (left/right/up/down)."""
        self._bb(x, y)
        self.raw(f'<circle class="{self.cls} o" cx="{x}" cy="{y}" r="3.5"/>')
        if side == 'left': self.text(x - 8, y + 4, label, 'end')
        elif side == 'right': self.text(x + 8, y + 4, label, 'start')
        elif side == 'up': self.text(x, y - 10 - 13 * label.count('\n'), label, 'middle')
        else: self.text(x, y + 18, label, 'middle')

    def ground(self, x, y):
        self.line((x, y), (x, y + 8))
        for i, w in enumerate((10, 6, 2)):
            self.line((x - w, y + 8 + i * 3.5), (x + w, y + 8 + i * 3.5))

    def rail(self, x, y, label):
        self.line((x, y), (x, y - 8)); self.line((x - 8, y - 8), (x + 8, y - 8))
        self.text(x, y - 13, label, 'middle')

    # ---- two-terminal parts between p1 and p2 (horizontal or vertical)
    def _two(self, p1, p2, L, draw, label, side):
        (x1, y1), (x2, y2) = p1, p2
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy); ux, uy = dx / n, dy / n
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        a = math.degrees(math.atan2(dy, dx))
        self.line(p1, (cx - ux * L / 2, cy - uy * L / 2))
        self.line((cx + ux * L / 2, cy + uy * L / 2), p2)
        self.raw(f'<g transform="translate({cx},{cy}) rotate({a:.0f})">{draw}</g>')
        for px, py in ((cx - 14, cy - 14), (cx + 14, cy + 14)): self._bb(px, py)
        if label:
            horiz = abs(dy) < 1e-6
            if horiz:
                if side in (None, 'up'): self.text(cx, cy - 14 - 13 * label.count('\n'), label, 'middle')
                else: self.text(cx, cy + 24, label, 'middle')
            else:
                if side in (None, 'right'): self.text(cx + 14, cy + 4 - 6 * label.count('\n'), label, 'start')
                else: self.text(cx - 14, cy + 4 - 6 * label.count('\n'), label, 'end')
        return cx, cy

    def res(self, p1, p2, label='', side=None):
        z = ' '.join(f'{-18 + i * 4},{0 if i in (0, 9) else (-5 if i % 2 else 5)}' for i in range(10))
        return self._two(p1, p2, 36, f'<polyline class="{self.cls}" points="{z}"/>', label, side)

    def cap(self, p1, p2, label='', side=None, polar=False):
        """polar: + plate is the p1 side."""
        d = f'<line class="{self.cls}" x1="-3" y1="-10" x2="-3" y2="10"/>'
        if polar:
            d += f'<path class="{self.cls}" d="M5,-10 Q1,0 5,10"/>'
            d += f'<text class="t {self.cls}t" x="-9" y="-6" font-size="10" text-anchor="middle">+</text>'
        else:
            d += f'<line class="{self.cls}" x1="3" y1="-10" x2="3" y2="10"/>'
        return self._two(p1, p2, 6 if not polar else 8, d, label, side)

    def diode(self, p1, p2, label='', side=None, led=False):
        """Anode p1, cathode p2."""
        d = (f'<polygon class="{self.cls}" points="-7,-8 -7,8 7,0"/>'
             f'<line class="{self.cls}" x1="7" y1="-8" x2="7" y2="8"/>')
        if led:
            for o in (-3, 3):
                d += (f'<line class="{self.cls}" x1="{o}" y1="-10" x2="{o + 6}" y2="-17"/>'
                      f'<polyline class="{self.cls}" points="{o + 2},-17 {o + 6},-17 {o + 6},-13"/>')
        return self._two(p1, p2, 14, d, label, side)

    def fuse(self, p1, p2, label='', side=None):
        d = (f'<rect class="{self.cls}" x="-14" y="-5" width="28" height="10" fill="none"/>'
             f'<line class="{self.cls}" x1="-14" y1="0" x2="14" y2="0"/>')
        return self._two(p1, p2, 28, d, label, side)

    def switch(self, p1, p2, label='', side=None):
        d = (f'<circle class="{self.cls} o" cx="-12" cy="0" r="2.5"/><circle class="{self.cls} o" cx="12" cy="0" r="2.5"/>'
             f'<line class="{self.cls}" x1="-10" y1="-1" x2="12" y2="-10"/>')
        return self._two(p1, p2, 24, d, label, side)

    def button(self, p1, p2, label='', side=None):
        d = (f'<circle class="{self.cls} o" cx="-10" cy="0" r="2.5"/><circle class="{self.cls} o" cx="10" cy="0" r="2.5"/>'
             f'<line class="{self.cls}" x1="-12" y1="-7" x2="12" y2="-7"/><line class="{self.cls}" x1="0" y1="-7" x2="0" y2="-13"/>')
        return self._two(p1, p2, 20, d, label, side)

    def pot(self, p1, p2, label='', side=None, wiper_side='right'):
        """Ends p1/p2 (vertical), wiper returned on wiper_side, 24 px out."""
        cx, cy = self.res(p1, p2, label, side)
        s = 1 if wiper_side == 'right' else -1
        wx = cx + s * 24
        self.line((wx, cy), (cx + s * 9, cy))
        self.raw(f'<polygon class="{self.cls} f" points="{cx + s * 7},{cy} {cx + s * 13},{cy - 4} {cx + s * 13},{cy + 4}"/>')
        self._bb(wx, cy)
        return wx, cy

    # ---- three-terminal
    def npn(self, cx, cy, label='', mirror=False):
        s = -1 if mirror else 1
        P = lambda x, y: (cx + s * x, cy + y)
        self.raw(f'<circle class="{self.cls}" cx="{cx}" cy="{cy}" r="15" fill="none"/>')
        self.line(P(-26, 0), P(-6, 0))
        self.line(P(-6, -9), P(-6, 9))
        self.line(P(-6, -4), P(8, -12), P(8, -26))
        self.line(P(-6, 4), P(8, 12), P(8, 26))
        ax, ay = P(8, 12); bx, by = P(1, 6.5)
        self.raw(f'<polygon class="{self.cls} f" points="{ax},{ay} {bx - s * 1},{by + 4.5} {bx + s * 2},{by - 2.5}"/>')
        for p in (P(-26, -15), P(18, 26)): self._bb(*p)
        for t, (x, y) in (('B', P(-22, -5)), ('C', P(13, -19)), ('E', P(13, 25))):
            self.text(x, y, t, 'middle', cls='t pin', size=9)
        if label:
            self.text(cx + s * 22, cy + 4, label, 'start' if s > 0 else 'end')
        return dict(B=P(-26, 0), C=P(8, -26), E=P(8, 26))

    def pmos(self, cx, cy, label=''):
        self.raw(f'<circle class="{self.cls}" cx="{cx}" cy="{cy}" r="17" fill="none"/>')
        self.line((cx - 28, cy), (cx - 9, cy))
        self.line((cx - 9, cy - 10), (cx - 9, cy + 10))
        for y0 in (-12, -3, 6): self.line((cx - 4, cy + y0), (cx - 4, cy + y0 + 6))
        self.line((cx - 4, cy - 9), (cx + 8, cy - 9), (cx + 8, cy - 28))
        self.line((cx - 4, cy + 9), (cx + 8, cy + 9), (cx + 8, cy + 28))
        self.line((cx - 4, cy), (cx + 8, cy), (cx + 8, cy - 9))
        self.raw(f'<polygon class="{self.cls} f" points="{cx + 4},{cy} {cx - 1},{cy - 4} {cx - 1},{cy + 4}"/>')
        for p in ((cx - 28, cy - 18), (cx + 18, cy + 28)): self._bb(*p)
        for t, (x, y) in (('G', (cx - 23, cy - 5)), ('S', (cx + 14, cy - 20)), ('D', (cx + 14, cy + 26))):
            self.text(x, y, t, 'middle', cls='t pin', size=9)
        if label: self.text(cx + 24, cy + 4, label)
        return dict(G=(cx - 28, cy), S=(cx + 8, cy - 28), D=(cx + 8, cy + 28))

    # ---- boxes (modules, connectors)
    def box(self, x, y, w, h, title, left=(), right=(), pitch=20, top=20):
        """left/right: lists of pin names (None = gap). Returns {name: (x,y)} for pin ends (12 px out)."""
        self._bb(x, y); self._bb(x + w, y + h)
        self.raw(f'<rect class="{self.cls} box" x="{x}" y="{y}" width="{w}" height="{h}" rx="3"/>')
        self.text(x + w / 2, y + h + 15, title, 'middle')
        pins = {}
        for i, n in enumerate(left):
            if n is None: continue
            py = y + top + i * pitch
            self.line((x - 12, py), (x, py)); pins[n] = (x - 12, py)
            self.text(x + 5, py + 4, n, 'start', size=10)
        for i, n in enumerate(right):
            if n is None: continue
            py = y + top + i * pitch
            self.line((x + w, py), (x + w + 12, py)); pins[n] = (x + w + 12, py)
            self.text(x + w - 5, py + 4, n, 'end', size=10)
        return pins

    def speaker(self, x, y):
        """Terminals at (x, y) and (x, y+20); cone to the right."""
        self.raw(f'<rect class="{self.cls} box" x="{x + 6}" y="{y - 2}" width="10" height="24"/>'
                 f'<polygon class="{self.cls}" points="{x + 16},{y - 2} {x + 30},{y - 14} {x + 30},{y + 34} {x + 16},{y + 22}" fill="none"/>')
        self.line((x, y), (x + 6, y)); self.line((x, y + 20), (x + 6, y + 20))
        self._bb(x + 32, y - 16); self._bb(x, y + 36)

    def note(self, x, y, s): self.text(x, y, s, cls='t dim')

    def svg(self, pad=16):
        x0, y0 = self.minx - pad, self.miny - pad
        w, h = self.maxx - self.minx + 2 * pad, self.maxy - self.miny + 2 * pad
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.0f} {y0:.0f} {w:.0f} {h:.0f}" '
                f'width="{w:.0f}" height="{h:.0f}" class="sch">' + ''.join(self.parts) + '</svg>')

STANDALONE_CSS = """<style>
.sch{font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;font-size:11px}
.bg{fill:#ffffff}
.w,.n,.x{fill:none;stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}
.w{stroke:#1f2630}.n{stroke:#c2185b}.x{stroke:#9aa1a9;stroke-dasharray:4 3}
.f.w{fill:#1f2630}.f.n{fill:#c2185b}.f.x{fill:#9aa1a9}
.o{fill:#ffffff}.box{fill:none}
.t{fill:#1f2630;stroke:none}.nt{fill:#c2185b}.xt{fill:#9aa1a9;text-decoration:line-through}.dim,.pin{fill:#5d6673}
@media (prefers-color-scheme: dark){
.bg,.o{fill:#0d1117}
.w{stroke:#dbe1e8}.f.w{fill:#dbe1e8}.t{fill:#dbe1e8}.dim,.pin{fill:#98a2ae}
.n{stroke:#f06a9b}.f.n{fill:#f06a9b}.nt{fill:#f06a9b}
}
</style>"""

def standalone(sheet):
    """Self-contained SVG file: own colors (light and dark) and a background, for markdown viewers."""
    s = sheet.svg()
    head, rest = s.split('class="sch">', 1)
    vb = head.split('viewBox="')[1].split('"')[0].split()
    bg = f'<rect class="bg" x="{vb[0]}" y="{vb[1]}" width="{vb[2]}" height="{vb[3]}" rx="6"/>'
    return head + 'class="sch">' + STANDALONE_CSS + bg + rest

def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

PREVIEW_CSS = """<style>
.sch{background:#fff;font-family:Helvetica,Arial,sans-serif;font-size:11px}
.w,.n,.x{fill:none;stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}
.w{stroke:#222}.n{stroke:#c2185b}.x{stroke:#999;stroke-dasharray:4 3}
.f.w{fill:#222}.f.n{fill:#c2185b}.f.x{fill:#999}
.o{fill:#fff}.box{fill:none}
.t{fill:#222;stroke:none}.nt{fill:#c2185b}.xt{fill:#999;text-decoration:line-through}.dim,.pin{fill:#777}
</style>"""

def preview(sheet, path):
    s = sheet.svg()
    s = s.replace('class="sch">', 'class="sch">' + PREVIEW_CSS, 1)
    open(path, 'w').write(s)
