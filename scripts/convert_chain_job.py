#!/usr/bin/env python3
"""
convert_chain_job.py — move a ';'-chained com.exos launchd job onto scripts/run_chain.py (exo3 theme 6).

  before: [..run_logged.py, L, --, /bin/zsh, -lc, "a; b; c"]
  after:  [..run_logged.py, L, --, /usr/bin/python3, <ws>/scripts/run_chain.py, --label, L,
           --shell, /bin/zsh, -lc, --, "a", "b", "c"]
  nested (task_ledger ... -- /bin/zsh -lc "a; b"): the inner quoted chain is rewritten to
           ... -- /usr/bin/python3 <ws>/scripts/run_chain.py --label L --shell /bin/zsh -lc -- 'a' 'b'

Backs up the plist once to ~/Library/LaunchAgents/.pre-runchain-backup/, lints the new one, then
(--reload) bootout+bootstrap only if the job is not running. --restore <label> puts the backup back and
reloads it. Only splits chains whose steps carry no quotes/&&/|| (refuses anything else).

Usage: convert_chain_job.py [--dry-run] [--reload] <label> ...
       convert_chain_job.py --restore <label> ...
"""
import os, plistlib, re, shlex, shutil, subprocess, sys

WS = "/Users/exomac/.openclaw/workspace"
LA = os.path.expanduser("~/Library/LaunchAgents")
BK = os.path.join(LA, ".pre-runchain-backup")
CHAIN = [f"/usr/bin/python3", f"{WS}/scripts/run_chain.py"]
UID = os.getuid()


def split_steps(s):
    steps = [x.strip() for x in s.split(";") if x.strip()]
    for x in steps:
        if re.search(r"[\"'`]|&&|\|\||\$\(", x):
            raise ValueError(f"step not simple enough to split safely: {x[:80]}")
    if len(steps) < 2:
        raise ValueError("no ';' chain")
    return steps


def rewrite(args, label):
    i = args.index("--") + 1
    shell, flag, cmd = args[i], args[i + 1], args[i + 2]
    if flag not in ("-c", "-lc") or len(args) != i + 3:
        raise ValueError("not a <shell> -c <string> job")
    if "run_chain.py" in cmd or args[i:i + 2] == CHAIN:
        raise ValueError("already converted")
    m = re.match(r'^(.* -- )(/bin/(?:zsh|sh)) (-lc|-c) "([^"]*)"$', cmd)
    if m:  # nested chain inside a single-command prefix (task_ledger run ... --)
        pre, ish, iflag, inner = m.groups()
        if ";" in pre:
            raise ValueError("prefix itself is chained")
        steps = split_steps(inner)
        new = pre + " ".join(CHAIN + ["--label", label, "--shell", ish, iflag, "--"] + [shlex.quote(x) for x in steps])
        return args[:i + 2] + [new]
    steps = split_steps(cmd)
    return args[:i] + CHAIN + ["--label", label, "--shell", shell, flag, "--"] + steps


def running(label):
    out = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        f = line.split("\t")
        if len(f) == 3 and f[2] == label:
            return f[0] != "-"
    return False


def reload(label, path):
    subprocess.run(["launchctl", "bootout", f"gui/{UID}/{label}"], capture_output=True)
    r = subprocess.run(["launchctl", "bootstrap", f"gui/{UID}", path], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


def convert(label, dry, do_reload):
    path = os.path.join(LA, label + ".plist")
    pl = plistlib.load(open(path, "rb"))
    new_args = rewrite(pl["ProgramArguments"], label)
    if dry:
        print(label, "->", new_args[new_args.index("--") + 1:]); return True
    if do_reload and running(label):
        print(f"SKIP {label}: running now"); return False
    os.makedirs(BK, exist_ok=True)
    bk = os.path.join(BK, label + ".plist")
    if not os.path.exists(bk):
        shutil.copy2(path, bk)
    pl["ProgramArguments"] = new_args
    tmp = path + ".runchain.tmp"
    plistlib.dump(pl, open(tmp, "wb"))
    if subprocess.run(["plutil", "-lint", tmp], capture_output=True).returncode != 0:
        os.remove(tmp); print(f"FAIL {label}: lint"); return False
    os.replace(tmp, path)
    if do_reload:
        ok, err = reload(label, path)
        if not ok:
            shutil.copy2(bk, path); reload(label, path)
            print(f"FAIL {label}: bootstrap ({err}); restored original"); return False
    print(f"OK {label}: converted{' + reloaded' if do_reload else ''}")
    return True


def restore(label):
    path, bk = os.path.join(LA, label + ".plist"), os.path.join(BK, label + ".plist")
    shutil.copy2(bk, path)
    ok, err = reload(label, path)
    print(f"{'OK' if ok else 'FAIL'} {label}: restored pre-runchain plist {err}")
    return ok


def main():
    a = sys.argv[1:]
    if "--restore" in a:
        return 0 if all(restore(l) for l in a if not l.startswith("--")) else 1
    dry, rl = "--dry-run" in a, "--reload" in a
    ok = True
    for l in [x for x in a if not x.startswith("--")]:
        try:
            ok &= convert(l, dry, rl)
        except (ValueError, KeyError) as e:
            print(f"SKIP {l}: {e}"); ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
