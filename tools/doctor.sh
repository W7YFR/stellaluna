#!/usr/bin/env bash
# Check that the Stellaluna workspace and its build tools are set up (`make doctor` runs it).
# Prints one line per check, with how to fix anything missing. Exits 1 if anything required is missing.
set -uo pipefail

HUB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS="$(dirname "$HUB")"
missing=0

ok()   { printf '  ok    %s\n' "$*"; }
warn() { printf '  warn  %s\n' "$1"; [[ -n "${2:-}" ]] && printf '        fix: %s\n' "$2"; }
bad()  { printf '  FAIL  %s\n' "$1"; [[ -n "${2:-}" ]] && printf '        fix: %s\n' "$2"; missing=1; }

brew_hint() { if command -v brew >/dev/null; then echo "brew install $1"; else echo "$2"; fi; }

tool() {  # tool <command> <what it's for> <brew formula> <other install hint> [optional]
  if command -v "$1" >/dev/null 2>&1; then ok "$1 ($2)"
  elif [[ -n "${5:-}" ]]; then warn "$1 not found ($2)" "$(brew_hint "$3" "$4")"
  else bad "$1 not found ($2)" "$(brew_hint "$3" "$4")"; fi
}

echo "Tools"
tool git "everything" git "https://git-scm.com"
tool make "these targets" make "install your OS's build tools (macOS: xcode-select --install)"
if command -v python3 >/dev/null && python3 -c 'import sys; sys.exit(sys.version_info < (3, 8))'; then
  ok "python3 $(python3 -c 'import platform; print(platform.python_version())') (schematics, keyer builds)"
else bad "python3 3.8+ not found (schematics, keyer builds)" "$(brew_hint python "https://www.python.org")"; fi
tool pio "PlatformIO: keyer and adapter builds" platformio "pip install platformio"
tool rsvg-convert "schematic previews (make schematics works without it)" librsvg "your OS's librsvg package" optional
tool exiftool "stripping photo metadata before adding images" exiftool "https://exiftool.org" optional
tool gh "GitHub CLI (optional)" gh "https://cli.github.com" optional

echo "Repos (in $WS)"
repo() {  # repo <folder> <branch> [optional]
  local d="$WS/$1"
  if [[ ! -d "$d/.git" ]]; then
    if [[ -n "${3:-}" ]]; then warn "$1 not cloned (private; only needed for VBand protocol work)" "make setup"
    else bad "$1 not cloned" "make setup"; fi
    return
  fi
  local b; b="$(git -C "$d" branch --show-current)"
  if [[ "$b" == "$2" ]]; then ok "$1 on $b"; else warn "$1 is on '$b' (usually $2)" "git -C $d switch $2"; fi
}
repo stellaluna main
repo k3ng_cw_keyer w7yfr
repo k3ng-vband-adapter main
repo vband main optional

if [[ -d "$WS/k3ng_cw_keyer/.git" ]]; then
  if git -C "$WS/k3ng_cw_keyer" remote get-url upstream >/dev/null 2>&1; then ok "k3ng_cw_keyer has the 'upstream' remote"
  else warn "k3ng_cw_keyer has no 'upstream' remote (K3NG)" "git -C $WS/k3ng_cw_keyer remote add upstream https://github.com/k3ng/k3ng_cw_keyer.git"; fi
fi
if [[ -d "$WS/k3ng-vband-adapter/.git" ]]; then
  if [[ -f "$WS/k3ng-vband-adapter/scripts/hydrate_build_flags.py" ]]; then ok "k3ng-vband-adapter build scripts (submodule)"
  else bad "k3ng-vband-adapter build scripts submodule not fetched" "git -C $WS/k3ng-vband-adapter submodule update --init"; fi
  if [[ -f "$WS/k3ng-vband-adapter/.env" ]]; then ok "k3ng-vband-adapter/.env present"
  else warn "k3ng-vband-adapter/.env missing (OTA and portal passwords; needed to build the adapter)" \
       "create it with OTA_PASSWORD, OTA_HOSTNAME and WIFI_MANAGER_AP_PASSWORD (git-ignored)"; fi
fi

echo "GitHub access"
host="$(git -C "$HUB" remote get-url origin 2>/dev/null | sed -n 's/^git@\([^:]*\):.*/\1/p')"
if [[ -n "$host" ]]; then
  # GitHub's SSH test exits 1 even when it works, so look at what it says instead.
  sshout="$(ssh -o BatchMode=yes -o ConnectTimeout=5 -T "git@$host" 2>&1 || true)"
  if [[ "$sshout" == *"successfully authenticated"* ]]; then
    ok "SSH to $host"
  else warn "SSH to $host failed (needed to push)" "check your SSH key / ~/.ssh/config entry for $host"; fi
else ok "origin uses HTTPS (pushing needs a credential helper or gh auth login)"; fi

echo "Keyer upstream map"
if [[ -f "$WS/k3ng_cw_keyer/UPSTREAM.md" ]]; then
  # fetches upstream and origin (reads only); a stale map or a moved upstream is a warning, not a failure
  if upout="$(python3 "$HUB/tools/keyer-upstream/check_upstream.py" --keyer "$WS/k3ng_cw_keyer" 2>&1)"; then
    ok "k3ng_cw_keyer/UPSTREAM.md matches the branches, and upstream master hasn't moved"
  else
    warn "k3ng_cw_keyer/UPSTREAM.md doesn't match the branches (or upstream moved, or the fetch failed):" \
         "update UPSTREAM.md (or rebase), then make keyer-upstream"
    printf '%s\n' "$upout" | sed 's/^/        /'
  fi
elif [[ -d "$WS/k3ng_cw_keyer/.git" ]]; then
  warn "k3ng_cw_keyer/UPSTREAM.md not found (is the keyer checkout on w7yfr?)"
fi

echo "PlatformIO platforms"
if command -v pio >/dev/null 2>&1; then
  for p in atmelavr espressif32; do
    if pio pkg list -g 2>/dev/null | grep -q "platform.*$p\|$p @" || [[ -d "$HOME/.platformio/platforms/$p" ]]; then ok "$p installed"
    else warn "$p not installed yet (downloads on the first build)" "pio pkg install -g -p $p"; fi
  done
fi

echo
if [[ $missing == 0 ]]; then echo "All required checks passed."; else echo "Some required checks failed: see 'fix:' above."; fi
exit $missing
