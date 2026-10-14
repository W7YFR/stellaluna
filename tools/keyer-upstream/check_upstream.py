#!/usr/bin/env python3
"""Check the keyer fork's UPSTREAM.md against git.

UPSTREAM.md (in the keyer checkout, on w7yfr) maps every fix/feature/chore/build branch back to upstream K3NG
master. This checks that the map is still true:

- every such branch is in the table, and every row is a branch; each is pushed and matches origin
- "Kind" matches the branch's prefix; "Upstream" and "Status" use the known words
- "Based on": each listed base shares commits with the branch, and every commit the branch has from another
  branch comes from a listed base (so a stack, or an earlier version of one, can't go unlisted)
- "In w7yfr": yes means merged; "copy <commit>" means that commit is on w7yfr with the same subject as the
  branch's own commit, and the branch itself isn't merged; no means neither
- upstream master hasn't moved on from the local master, and every branch is cut from that master

It only reads: it fetches upstream (unless --no-fetch) and never pushes or writes anywhere.

  check_upstream.py                    # the keyer checkout next to this repo
  check_upstream.py --keyer PATH --no-fetch
"""

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KEYER = os.path.normpath(os.path.join(HERE, "..", "..", "..", "k3ng_cw_keyer"))
PREFIXES = ("fix", "feature", "chore", "build")
UPSTREAM_WORDS = {"ready", "needs work", "not for upstream"}
STATUS_RE = re.compile(r"^(not offered|PR #\d+|merged upstream|declined)$")


class Repo:
    def __init__(self, path):
        self.path = path

    def git(self, *args, check=True):
        r = subprocess.run(["git", "-C", self.path, *args], capture_output=True, text=True)
        if check and r.returncode != 0:
            raise SystemExit("git %s failed: %s" % (" ".join(args), r.stderr.strip()))
        return r.stdout.strip()

    def ok(self, *args):
        return subprocess.run(["git", "-C", self.path, *args], capture_output=True).returncode == 0

    def commits(self, rng):
        out = self.git("rev-list", rng)
        return set(out.split()) if out else set()


def read_table(path):
    """The Branches table: {branch: {kind, bases, w7yfr, upstream, status}}."""
    rows = {}
    with open(path) as f:
        for line in f:
            if not line.startswith("| `"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 7:
                continue
            branch = cells[0].strip("`")
            rows[branch] = {
                "kind": cells[1],
                "bases": re.findall(r"`([^`]+)`", cells[2]),
                "w7yfr": cells[3],
                "upstream": cells[4],
                "status": cells[5],
            }
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keyer", default=DEFAULT_KEYER, help="the keyer checkout (default: %(default)s)")
    ap.add_argument("--no-fetch", action="store_true", help="don't fetch upstream and origin first")
    args = ap.parse_args()

    repo = Repo(args.keyer)
    table_path = os.path.join(args.keyer, "UPSTREAM.md")
    if not os.path.exists(table_path):
        raise SystemExit("%s not found (is the keyer checkout on w7yfr?)" % table_path)
    problems = []

    if not args.no_fetch:
        repo.git("fetch", "-q", "upstream", "master")
        repo.git("fetch", "-q", "origin")

    # upstream master
    if repo.ok("rev-parse", "--verify", "-q", "upstream/master"):
        new = int(repo.git("rev-list", "--count", "master..upstream/master"))
        if new:
            problems.append("upstream master has %d commit(s) the local master doesn't: update master "
                            "(git -C %s merge --ff-only upstream/master), then rebase the branches" % (new, repo.path))
    else:
        problems.append("no upstream/master: add the remote (make setup does) and fetch it")
    master = repo.git("rev-parse", "master")

    branches = [b for b in repo.git("for-each-ref", "--format=%(refname:short)", "refs/heads").split()
                if b.split("/")[0] in PREFIXES]
    table = read_table(table_path)

    for b in sorted(set(branches) - set(table)):
        problems.append("%s: a branch, but not in UPSTREAM.md" % b)
    for b in sorted(set(table) - set(branches)):
        problems.append("%s: in UPSTREAM.md, but there's no such branch" % b)
    listed = [b for b in branches if b in table]

    own = {b: repo.commits("master.." + b) for b in listed}

    # each commit's home: the smallest branch that has it, i.e. the one it was made on
    home = {}
    for b in sorted(listed, key=lambda x: len(own[x])):
        for c in own[b]:
            home.setdefault(c, b)

    for b in listed:
        row = table[b]

        if row["kind"] != b.split("/")[0]:
            problems.append("%s: Kind is %r, the prefix says %r" % (b, row["kind"], b.split("/")[0]))
        if row["upstream"] not in UPSTREAM_WORDS:
            problems.append("%s: Upstream %r isn't one of %s" % (b, row["upstream"], ", ".join(sorted(UPSTREAM_WORDS))))
        if not STATUS_RE.match(row["status"]):
            problems.append("%s: Status %r isn't 'not offered', 'PR #n', 'merged upstream' or 'declined'"
                            % (b, row["status"]))

        # pushed, and the same as origin
        if not repo.ok("rev-parse", "--verify", "-q", "origin/" + b):
            problems.append("%s: not pushed to origin" % b)
        elif repo.git("rev-parse", b) != repo.git("rev-parse", "origin/" + b):
            problems.append("%s: differs from origin/%s (push or pull)" % (b, b))

        # cut from the current master
        if repo.git("merge-base", b, "master") != master:
            problems.append("%s: cut from an older master; rebase it on master" % b)

        # bases
        bases = [x for x in row["bases"] if x != "master"]
        for base in bases:
            if base not in own:
                problems.append("%s: based on %s, which isn't a listed branch" % (b, base))
            elif not (own[base] & own[b]):
                problems.append("%s: listed as based on %s, but has none of its commits" % (b, base))
        covered = set().union(*(own[x] for x in bases if x in own)) if bases else set()
        foreign = {home[c] for c in own[b] if home[c] != b and c not in covered}
        for other in sorted(foreign):
            problems.append("%s: has commits from %s, which isn't among its bases" % (b, other))

        # in w7yfr
        merged = repo.ok("merge-base", "--is-ancestor", b, "w7yfr")
        w = row["w7yfr"]
        if w == "yes":
            if not merged:
                problems.append("%s: In w7yfr says yes, but it isn't merged into w7yfr" % b)
        elif w.startswith("copy"):
            m = re.search(r"`?([0-9a-f]{7,40})`?", w)
            if merged:
                problems.append("%s: In w7yfr says copy, but the branch is merged (say yes)" % b)
            elif not m or not repo.ok("merge-base", "--is-ancestor", m.group(1), "w7yfr"):
                problems.append("%s: In w7yfr names a copy that isn't on w7yfr" % b)
            else:
                made_here = [c for c in own[b] if home[c] == b and c not in covered]
                subjects = {repo.git("log", "-1", "--format=%s", c) for c in made_here}
                if repo.git("log", "-1", "--format=%s", m.group(1)) not in subjects:
                    problems.append("%s: the copy %s has a different subject from the branch's own commits"
                                    % (b, m.group(1)))
        elif w == "no":
            if merged:
                problems.append("%s: In w7yfr says no, but it's merged" % b)
        else:
            problems.append("%s: In w7yfr %r isn't yes, copy <commit> or no" % (b, w))

    if problems:
        print("UPSTREAM.md doesn't match git:")
        for p in problems:
            print("  - " + p)
        return 1
    print("UPSTREAM.md matches git: %d branches, all pushed and cut from master %s (upstream hasn't moved)"
          % (len(listed), master[:7]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
