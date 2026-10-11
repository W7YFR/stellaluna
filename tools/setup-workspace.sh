#!/usr/bin/env bash
# Clone the other Stellaluna repos next to this one (run from anywhere; `make setup` runs it).
# Anything already there is left alone. Clones over the same host as this repo's own remote, so an SSH
# alias (git@my-alias:W7YFR/stellaluna.git) carries over; set GIT_PREFIX to override, for example
#   GIT_PREFIX=https://github.com/ make setup
set -euo pipefail

HUB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WS="$(dirname "$HUB")"

origin="$(git -C "$HUB" remote get-url origin 2>/dev/null || true)"
if [[ -z "${GIT_PREFIX:-}" ]]; then
  case "$origin" in
    git@*:W7YFR/*) GIT_PREFIX="${origin%%:*}:" ;;
    https://*)     GIT_PREFIX="https://github.com/" ;;
    *)             GIT_PREFIX="git@github.com:" ;;
  esac
fi

say() { printf '%s\n' "$*"; }

clone() {  # clone <github repo> <folder> <branch> [optional]
  local repo="$1" dir="$WS/$2" branch="$3" optional="${4:-}"
  if [[ -d "$dir/.git" ]]; then say "ok      $2 (already there)"; return 0; fi
  if [[ -e "$dir" ]]; then say "SKIP    $2: exists but isn't a git checkout"; return 0; fi
  if git clone -q -b "$branch" "${GIT_PREFIX}${repo}.git" "$dir" 2>/dev/null; then
    say "cloned  $2 ($branch)"
  elif [[ -n "$optional" ]]; then
    say "skip    $2: no access to $repo (private; fine unless you work on the VBand protocol)"
    return 0
  else
    say "FAIL    $2: couldn't clone ${GIT_PREFIX}${repo}.git"; return 1
  fi
}

say "workspace: $WS"
clone W7YFR/k3ng_cw_keyer k3ng_cw_keyer w7yfr
clone W7YFR/k3ng-vband-adapter k3ng-vband-adapter main
clone W7YFR/vband vband main optional

# The keyer fork tracks upstream K3NG for merges.
if [[ -d "$WS/k3ng_cw_keyer/.git" ]] && ! git -C "$WS/k3ng_cw_keyer" remote get-url upstream >/dev/null 2>&1; then
  git -C "$WS/k3ng_cw_keyer" remote add upstream https://github.com/k3ng/k3ng_cw_keyer.git
  git -C "$WS/k3ng_cw_keyer" fetch -q upstream && say "added   k3ng_cw_keyer remote 'upstream' (k3ng)"
fi

# The adapter's build scripts are a submodule.
if [[ -d "$WS/k3ng-vband-adapter/.git" ]]; then
  git -C "$WS/k3ng-vband-adapter" submodule update --init -q && say "ok      k3ng-vband-adapter submodules"
  if [[ ! -f "$WS/k3ng-vband-adapter/.env" ]]; then
    say "note    k3ng-vband-adapter/.env is missing: create it with OTA_PASSWORD, OTA_HOSTNAME and"
    say "        WIFI_MANAGER_AP_PASSWORD (see the adapter's README). It's git-ignored; never commit it."
  fi
fi

say ""
say "Next: make doctor"
