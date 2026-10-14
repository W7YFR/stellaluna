# keyer-upstream

Checks the keyer fork's `UPSTREAM.md` against git. That file maps every `fix/`, `feature/`, `chore/` and `build/`
branch back to upstream K3NG `master`: what it's cut from, whether it's in `w7yfr`, how ready it is to offer
upstream, and whether it has been. This keeps the map from drifting.

`make doctor` runs it too, and warns (without failing) if the map is out of date or upstream has moved.

```sh
make keyer-upstream                                        # the keyer checkout next to this repo
python3 tools/keyer-upstream/check_upstream.py --no-fetch  # without fetching upstream and origin first
```

It checks:

- every such branch has a row, and every row is a branch; each is pushed and the same as `origin`
- "Kind" matches the prefix; "Upstream" is ready / needs work / not for upstream; "Status" is not offered,
  `PR #n`, merged upstream or declined
- "Based on": each listed base shares commits with the branch, and any commit the branch has from another branch
  comes from a listed base. A commit belongs to the smallest branch that has it, so a branch cut from an earlier
  version of another (as `feature/settings-menu` is from `feature/vband-link`) is still caught if unlisted
- "In `w7yfr`": `yes` is merged; `copy <commit>` is a commit on `w7yfr` with the same subject as the branch's own
  commit (it was committed there directly), with the branch itself not merged; `no` is neither
- upstream `master` hasn't moved on from the local `master`, and every branch is cut from that `master`

It only reads: it fetches `upstream` and `origin` and never pushes, and never opens anything upstream. It prints
"matches" or a list of what to fix, and exits 1 if anything doesn't match.
