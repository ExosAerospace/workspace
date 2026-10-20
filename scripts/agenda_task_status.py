#!/usr/bin/env python3
"""agenda_task_status.py — stamp the live Mission Control status next to every task reference in a meeting agenda.

Lizi 2026-10-20 (ALL future meeting agendas): "anytime you reference a task in the meeting agenda can you note
the task status in mission control? to do, in progress or done?"  -> "#1712" becomes "#1712 [In Progress]".
Companion rule (same day): cancelled tasks never go on an agenda at all; any that slip through are tagged
[Cancelled] so they are obvious.

Use from agenda builders:
    import agenda_task_status as ats
    text = ats.annotate_text(text)        # plain-text / email agendas
    ats.annotate_docx(path)               # .docx agendas, rewritten in place (call after d.save)
CLI:
    agenda_task_status.py <agenda.docx|.txt> [...]
    agenda_task_status.py --selftest
"""
import json, os, re, sys, urllib.request

SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
REF = re.compile(r"#(\d{2,5})(?!\d|\.\d|\s*\[)")   # skip "#123.2" line keys and refs already stamped "#123 [..."
LABEL = {"to do": "To Do", "todo": "To Do", "backlog": "To Do", "open": "To Do", "not started": "To Do",
         "in progress": "In Progress", "in-progress": "In Progress", "doing": "In Progress", "blocked": "Blocked",
         "review": "In Review", "in review": "In Review",
         "done": "Done", "completed": "Done", "closed": "Done", "archived": "Done",
         "cancelled": "Cancelled", "canceled": "Cancelled"}


def _key():
    return json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]


def fetch_states(ids):
    ids = sorted({int(i) for i in ids})
    out, key = {}, None
    for i in range(0, len(ids), 80):
        key = key or _key()
        chunk = ",".join(map(str, ids[i:i + 80]))
        r = urllib.request.Request(f"{SB}/tasks?id=in.({chunk})&select=id,state",
                                   headers={"apikey": key, "Authorization": "Bearer " + key})
        with urllib.request.urlopen(r, timeout=40) as resp:
            for t in json.loads(resp.read().decode() or "[]"):
                out[t["id"]] = t.get("state") or ""
    return out


def label(state):
    return LABEL.get((state or "").strip().lower(), (state or "").strip() or "?")


def _stamp(s, states):
    return REF.sub(lambda m: f"#{m.group(1)} [{label(states[int(m.group(1))])}]"
                   if int(m.group(1)) in states else m.group(0), s)


def annotate_text(s, states=None):
    if states is None:
        states = fetch_states(int(x) for x in REF.findall(s))
    return _stamp(s, states)


def _paragraphs(doc):
    def walk(container):
        for p in container.paragraphs:
            yield p
        for t in getattr(container, "tables", []):
            for row in t.rows:
                for cell in row.cells:
                    yield from walk(cell)
    yield from walk(doc)
    for sec in doc.sections:
        for part in (sec.header, sec.footer):
            yield from walk(part)


def annotate_docx(path, states=None):
    from docx import Document
    doc = Document(path)
    paras = list(_paragraphs(doc))
    if states is None:
        states = fetch_states(int(x) for p in paras for x in REF.findall(p.text))
    n = 0
    for p in paras:
        if not REF.search(p.text):
            continue
        for r in p.runs:                       # normal case: ref sits inside one run, formatting kept
            new = _stamp(r.text, states)
            if new != r.text:
                r.text = new; n += 1
        if REF.search(p.text) and any(int(x) in states for x in REF.findall(p.text)) and p.runs:
            # ref split across runs: collapse into the first run
            full = _stamp(p.text, states)
            p.runs[0].text = full
            for r in p.runs[1:]:
                r.text = ""
            n += 1
    doc.save(path)
    return n


def _selftest():
    st = {1712: "In Progress", 1872: "Cancelled", 76: "To Do", 2409: "Completed"}
    s = "Phil #4: schedule on #1712; fins #76; tanks #2409; old #1872; stamped #1712 [In Progress]; line #1712.3"
    out = annotate_text(s, st)
    assert out == ("Phil #4: schedule on #1712 [In Progress]; fins #76 [To Do]; tanks #2409 [Done]; "
                   "old #1872 [Cancelled]; stamped #1712 [In Progress]; line #1712.3"), out
    assert annotate_text(out, st) == out          # idempotent
    import tempfile
    from docx import Document
    p = os.path.join(tempfile.mkdtemp(), "a.docx")
    d = Document(); d.add_paragraph("Target on #1712"); t = d.add_table(rows=1, cols=1); t.rows[0].cells[0].text = "#76"
    sp = d.add_paragraph(); sp.add_run("#24"); sp.add_run("09 split")
    d.save(p)
    annotate_docx(p, st)
    txt = [x.text for x in Document(p).paragraphs] + [Document(p).tables[0].rows[0].cells[0].text]
    assert "Target on #1712 [In Progress]" in txt and "#76 [To Do]" in txt and "#2409 [Done] split" in txt, txt
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest(); sys.exit(0)
    for f in sys.argv[1:]:
        if f.endswith(".docx"):
            print(f, annotate_docx(f), "paragraphs stamped")
        else:
            s = open(f).read(); open(f, "w").write(annotate_text(s)); print(f, "stamped")
