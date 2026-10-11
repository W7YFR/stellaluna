#!/usr/bin/env python3
"""Build the K3NG keyer firmware from any checkout or worktree, on any branch.

Upstream `master` (and feature branches cut from it) has no PlatformIO setup, so this copies the sketch to a
scratch folder, adds a known platformio.ini, applies the two small fixes PlatformIO builds need, applies the
preset's feature toggles, and builds. It never uploads.

    keyer-build.py                              # the as-is preset, on ../k3ng_cw_keyer
    keyer-build.py --keyer ~/wt/my-branch -p w7yfr-features -D FEATURE_NEW_THING
    keyer-build.py --matrix                     # every preset in presets/matrix.txt

Presets are text files in presets/ (see presets/as-is.txt):
    board <platformio board>      hardware HARDWARE_xxx      include <preset>
    +NAME   define NAME           -NAME   comment out NAME's #define in the copy
    =NAME VALUE   set a valued #define in the copy (for example =NUMBER_OF_EXTRA_BUTTONS 2)
    lib <platformio library>      an extra library the profile needs (for example lib arduino-libraries/Ethernet)
    flag <compiler flag>          an extra compiler flag (for example flag -Wno-narrowing)
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PRESETS = os.path.join(HERE, 'presets')
DEFAULT_KEYER = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'k3ng_cw_keyer'))
BUILD_ROOT = os.path.join(tempfile.gettempdir(), 'stellaluna-keyer-build')

# PlatformIO's .ino prototype scanner needs these. They live on the fork's build/platformio and
# fix/prosign-forward-declaration branches; each is applied only if the checkout doesn't have it already.
FIXES = [
    ('keyer_dependencies.h', 'void lcd_center_print_timed_wpm();',
     '#if defined(FEATURE_COMMAND_LINE_INTERFACE_ON_SECONDARY_PORT) && !defined(FEATURE_COMMAND_LINE_INTERFACE)',
     '#ifdef FEATURE_DISPLAY\n  void lcd_center_print_timed_wpm();  // keyer-build: PlatformIO prototype fix\n#endif\n\n'),
    ('k3ng_keyer.ino', '#define NETWORK_CLIENT_CLS int', '#define memory_area_start',
     '#ifndef NETWORK_CLIENT_CLS\n  #define NETWORK_CLIENT_CLS int  // keyer-build: PlatformIO prototype fix\n#endif\n\n'),
    ('k3ng_keyer.ino', 'char * convert_prosign(byte prosign_code);', '#include "keyer_debug.h"\n',
     None),  # inserted after the anchor, below
]
PROSIGN_FIX = ('#if defined(OPTION_PROSIGN_SUPPORT)\n  char * convert_prosign(byte prosign_code);  // keyer-build: PlatformIO prototype fix\n'
               '#endif\n')

def load_preset(name, seen=()):
    path = os.path.join(PRESETS, name + '.txt')
    if not os.path.exists(path): sys.exit(f'no preset {name!r} (presets: {", ".join(list_presets())})')
    if name in seen: sys.exit(f'preset include loop at {name}')
    p = {'board': None, 'hardware': None, 'on': [], 'off': [], 'set': [], 'lib': [], 'flag': []}
    for raw in open(path):
        line = raw.split('#', 1)[0].strip()
        if not line: continue
        if line.startswith('include '):
            inc = load_preset(line.split(None, 1)[1], seen + (name,))
            for k in ('board', 'hardware'): p[k] = p[k] or inc[k]
            for k in ('on', 'off', 'set', 'lib', 'flag'): p[k] = inc[k] + p[k]
        elif line.startswith('board '): p['board'] = line.split(None, 1)[1]
        elif line.startswith('hardware '): p['hardware'] = line.split(None, 1)[1]
        elif line.startswith('lib '): p['lib'].append(line.split(None, 1)[1])
        elif line.startswith('flag '): p['flag'].append(line.split(None, 1)[1])
        elif line[0] == '+': p['on'].append(line[1:].strip())
        elif line[0] == '-': p['off'].append(line[1:].strip())
        elif line[0] == '=':
            k, v = line[1:].split(None, 1); p['set'].append((k, v))
        else: sys.exit(f'{path}: can\'t read {raw.strip()!r}')
    return p

def list_presets():
    return sorted(f[:-4] for f in os.listdir(PRESETS) if f.endswith('.txt') and f != 'matrix.txt')

def prepare(keyer, name, preset, extra_on, extra_off, extra_set):
    src = os.path.join(keyer, 'k3ng_keyer')
    if not os.path.isfile(os.path.join(src, 'k3ng_keyer.ino')): sys.exit(f'{keyer} is not a keyer checkout')
    tag = re.sub(r'[^A-Za-z0-9]+', '-', os.path.abspath(keyer)).strip('-')[-60:]
    build = os.path.join(BUILD_ROOT, tag, name)
    sketch = os.path.join(build, 'k3ng_keyer')
    if os.path.exists(sketch): shutil.rmtree(sketch)  # keep .pio/ between runs: it caches the libraries
    shutil.copytree(src, sketch)
    notes = []
    for fname, marker, anchor, insert in FIXES:
        p = os.path.join(sketch, fname)
        s = open(p, encoding='latin-1').read()
        if marker not in s:
            if anchor not in s: sys.exit(f'can\'t apply the PlatformIO fix to {fname}: {anchor!r} not found')
            s = s.replace(anchor, anchor + PROSIGN_FIX if insert is None else insert + anchor, 1)
            open(p, 'w', encoding='latin-1').write(s)
            notes.append(f'applied PlatformIO fix to {fname}')
    headers = [os.path.join(sketch, f) for f in os.listdir(sketch) if f.startswith('keyer_') and f.endswith('.h')]
    for nm in preset['off'] + extra_off:
        hit = 0
        for h in headers:
            s = open(h, encoding='latin-1').read()
            s2, k = re.subn(r'(?m)^(\s*)#define\s+' + re.escape(nm) + r'\b', r'\1// keyer-build off: #define ' + nm, s)
            if k: open(h, 'w', encoding='latin-1').write(s2); hit += k
        if not hit: notes.append(f'-{nm}: no #define found (already off?)')
    for nm, val in preset['set'] + extra_set:
        hit = 0
        for h in headers:
            s = open(h, encoding='latin-1').read()
            s2, k = re.subn(r'(?m)^(\s*#define\s+' + re.escape(nm) + r'\s+)\S+', lambda m: m.group(1) + val, s)
            if k: open(h, 'w', encoding='latin-1').write(s2); hit += k
        if not hit: notes.append(f'={nm}: no #define found to set')
    flags = [f'-D {d}' for d in preset['on'] + extra_on]
    if preset['hardware']: flags.append(f'-D {preset["hardware"]}')
    flags += preset['flag']
    libs = os.path.join(os.path.abspath(keyer), 'libraries')
    ini = f"""; generated by stellaluna/tools/keyer-build
[platformio]
src_dir = k3ng_keyer

[env:build]
platform = atmelavr
board = {preset['board'] or 'megaatmega2560'}
framework = arduino
lib_extra_dirs = {libs}
lib_ldf_mode = deep+
lib_deps = {chr(10).join('    ' + l for l in ['greiman/SSD1306Ascii', 'arduino-libraries/LiquidCrystal'] + preset['lib']).strip()}
build_flags = {' '.join(flags)}
"""
    open(os.path.join(build, 'platformio.ini'), 'w').write(ini)
    return build, notes

def run(build, verbose):
    log = os.path.join(build, 'build.log')
    with open(log, 'w') as fh:
        r = subprocess.run(['pio', 'run', '-d', build], stdout=fh, stderr=subprocess.STDOUT)
    out = open(log, encoding='utf-8', errors='replace').read()
    if verbose: print(out)
    ram = re.search(r'RAM:\s+\[[^\]]*\]\s+([\d.]+)%\s+\(used (\d+) bytes', out)
    flash = re.search(r'Flash:\s+\[[^\]]*\]\s+([\d.]+)%\s+\(used (\d+) bytes', out)
    errors = [re.sub(r'^\S*/k3ng_keyer/', '', l) for l in out.splitlines()
              if re.search(r'\berror\b|undefined reference', l) and 'collect2' not in l]
    errors = list(dict.fromkeys(errors))[:15]
    return r.returncode == 0, ram, flash, errors, log

def error_key(line):
    """An error without its file/line position, so the same error on another branch compares equal."""
    return re.sub(r'^[^:]*:\d+:\d+:\s*', '', line).strip()

def baseline(keyer, ref, names, args):
    """Errors each preset gets on `ref` (cached per commit), for telling new errors from old ones."""
    sha = subprocess.run(['git', '-C', keyer, 'rev-parse', ref], capture_output=True, text=True).stdout.strip()
    if not sha: sys.exit(f'--compare: no such ref {ref!r} in {keyer}')
    cache_path = os.path.join(BUILD_ROOT, 'baseline-cache.json')
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    flags = ' '.join(args.on + ['-U' + x for x in args.off] + args.set)
    todo = [n for n in names if f'{sha}|{n}|{flags}' not in cache]
    if todo:
        wt = tempfile.mkdtemp(prefix='keyer-base-')
        subprocess.run(['git', '-C', keyer, 'worktree', 'add', '-q', '--detach', wt, sha], check=True)
        try:
            print(f'baseline: {ref} ({sha[:7]}), building {len(todo)} preset(s) once')
            for n in todo:
                build, _ = prepare(wt, n, load_preset(n), args.on, args.off, [tuple(x.split('=', 1)) for x in args.set])
                ok, _, _, errors, _ = run(build, False)
                cache[f'{sha}|{n}|{flags}'] = {'ok': ok, 'errors': sorted({error_key(e) for e in errors})}
                print(f'  {"ok  " if ok else "FAIL"}  {n} on {ref}')
        finally:
            subprocess.run(['git', '-C', keyer, 'worktree', 'remove', '--force', wt])
        os.makedirs(BUILD_ROOT, exist_ok=True)
        json.dump(cache, open(cache_path, 'w'), indent=1)
    return {n: cache[f'{sha}|{n}|{flags}'] for n in names}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--keyer', default=DEFAULT_KEYER, help='keyer checkout or worktree (default: ../k3ng_cw_keyer)')
    ap.add_argument('-p', '--preset', action='append', help='preset name (repeatable); default as-is')
    ap.add_argument('--matrix', action='store_true', help='build every preset in presets/matrix.txt')
    ap.add_argument('-D', dest='on', action='append', default=[], metavar='NAME', help='also define NAME')
    ap.add_argument('-U', dest='off', action='append', default=[], metavar='NAME', help='also comment out NAME')
    ap.add_argument('--set', action='append', default=[], metavar='NAME=VALUE', help='also set a valued define')
    ap.add_argument('--compare', metavar='REF', help='also build each preset on REF (for example master) and only '
                    'count errors REF doesn\'t already have')
    ap.add_argument('--list', action='store_true', help='list presets')
    ap.add_argument('-v', '--verbose', action='store_true', help='print the full build output')
    a = ap.parse_args()
    if a.list: print('\n'.join(list_presets())); return
    if not shutil.which('pio'): sys.exit('PlatformIO (pio) not found: brew install platformio')
    if a.matrix:
        names = [l.split('#')[0].strip() for l in open(os.path.join(PRESETS, 'matrix.txt'))]
        names = [n for n in names if n]
    else:
        names = a.preset or ['as-is']
    extra_set = [tuple(s.split('=', 1)) for s in a.set]
    branch = subprocess.run(['git', '-C', a.keyer, 'rev-parse', '--abbrev-ref', 'HEAD'],
                            capture_output=True, text=True).stdout.strip() or '?'
    base = baseline(a.keyer, a.compare, names, a) if a.compare else {}
    print(f'keyer: {a.keyer} ({branch})')
    failed = 0
    for n in names:
        build, notes = prepare(a.keyer, n, load_preset(n), a.on, a.off, extra_set)
        ok, ram, flash, errors, log = run(build, a.verbose)
        size = (f'RAM {ram.group(1)}% ({ram.group(2)} B)' if ram else 'RAM ?') + ', ' + \
               (f'flash {flash.group(1)}%' if flash else 'flash ?')
        new = errors
        if not ok and n in base and not base[n]['ok']:
            new = [e for e in errors if error_key(e) not in set(base[n]['errors'])]
        status = 'ok  ' if ok else ('old ' if not new else 'FAIL')
        print(f'  {status}  {n:<18} {size}' + (f'   (fails the same way on {a.compare})' if status == 'old ' else ''))
        for note in notes: print(f'        note: {note}')
        if status == 'FAIL':
            failed += 1
            for e in new: print('        ' + e.strip()[:160])
            print(f'        log: {log}')
    sys.exit(1 if failed else 0)

if __name__ == '__main__':
    main()
