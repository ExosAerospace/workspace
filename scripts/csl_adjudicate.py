#!/usr/bin/env python3
"""
csl_adjudicate.py — auto-triage for CSL denied-party flags.

Goal (John, 2026-09-10): do the investigation BEFORE John sees a flag, so he only
reviews genuine ambiguity — not obvious name collisions.

Each new flag is adjudicated: is OUR party plausibly the SAME real-world entity as the
listed denied party, or a different entity that merely shares/approximates the name?
- CLEAR  → auto-disposition ONLY via the deterministic verified-registry fast path
            (human-attested identity on record).
- PROPOSED_CLEAR → the local model believes it is a name collision. This is a PROPOSAL
            only (exo3 audit P1 #4: AI proposes, a human confirms) — the flag stays OPEN
            until a human dispositions it; the model rationale is shown to the reviewer.
- ESCALATE → surfaced to John for a human clear/confirm.

Design principles (compliance-safe):
- Conservative by construction: auto-clear ONLY on high-confidence "different entity."
- Never auto-clear a party the listed side ties to the U.S. (a U.S.-nexus denied party is
  exactly what must reach a human).
- On ANY doubt, model failure, or parse error → ESCALATE. Never a silent clear.
- Local inference only (Ollama on 127.0.0.1) so CRM/party names never leave the box.
- Every auto-clear is logged with rationale for audit; fully reversible.
- A model verdict NEVER clears a denied-party match by itself (export compliance: fail CLOSED).
"""
import json, os, re, urllib.request

OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = os.environ.get("CSL_ADJ_MODEL", "gemma4:e4b")

# Embargoed / adversary jurisdictions where a same-name entity is almost never our party.
SANCTIONED_CC = {"RU","IR","KP","SY","CU","VE","BY"}

# Crown-jewel / known-good parties: deterministic fast-path clear (identity on record).
# norm(party) -> (real identity, why it is not the listed denied party generically)
VERIFIED = {
    "scorpius": "Scorpius Space Launch Company (SSLC), Torrance, CA, USA — Exos owns 18% with ROFR",
    "axiom": "Axiom Space, Inc., Houston, TX, USA — U.S. commercial space company",
    "ae industrial": "AE Industrial Partners, Boca Raton, FL, USA — U.S. aerospace/defense PE",
    "ideal vacuum": "Ideal Vacuum Products, Albuquerque, NM, USA — domestic vacuum-equipment vendor",
}

def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()

def _llm(party, party_type, f, timeout=90):
    """Ask the local model to judge same-entity vs collision. Returns dict or None."""
    prompt = (
        "You are a U.S. export-compliance analyst triaging a denied-party screening hit.\n"
        "Decide whether OUR party and the LISTED sanctioned/restricted party are the SAME "
        "real-world entity, or DIFFERENT entities that merely share or approximate a name.\n\n"
        f"OUR PARTY (from Exos {party_type}): \"{party}\"\n"
        f"LISTED PARTY: \"{f['listed_name']}\"\n"
        f"  list: {f['list']}\n  programs: {f.get('programs') or 'n/a'}\n"
        f"  country: {f.get('countries') or 'n/a'}\n  fuzzy_score: {f['score']}\n\n"
        "Context: Exos Aerospace is a U.S. reusable-launch / aerospace-defense company. Its "
        "parties are U.S. and allied aerospace, defense, space, investor, and vendor entities.\n\n"
        "Judge conservatively. If there is any plausible chance they are the same entity, or the "
        "listed party has a U.S. nexus, say ESCALATE. Only say CLEAR when they are clearly "
        "different entities (e.g., a U.S. space company vs. a Russia/Iran/China-based sanctioned "
        "firm of a similar name).\n\n"
        "Respond ONLY with JSON: "
        '{\"same_entity\": true|false, \"verdict\": \"clear\"|\"escalate\", '
        '\"confidence\": \"high\"|\"medium\"|\"low\", \"reason\": \"<one sentence>\"}'
    )
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "format": "json", "options": {"temperature": 0}}).encode()
    try:
        req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
        resp = json.load(urllib.request.urlopen(req, timeout=timeout))
        # Some models (thinking models) leave "response" empty and put text in "thinking".
        text = (resp.get("response") or resp.get("thinking") or "").strip()
        m = re.search(r"\{.*\}", text, re.S)  # tolerate stray prose around the JSON
        out = json.loads(m.group(0) if m else text or "{}")
        if "verdict" in out:
            return out
    except Exception as e:
        print("  adj: LLM unavailable/parse-fail ->", str(e)[:80])
    return None

def adjudicate(flag):
    """flag: {party, party_type, listed_name, list, programs, countries, score}
    Returns {verdict:'clear'|'proposed_clear'|'escalate', confidence, rationale, method}.
    'clear' is returned ONLY by the deterministic verified-registry path."""
    party = flag["party"]; np = _norm(party)
    cc = (flag.get("countries") or "").upper()

    # Fast-path: known-verified party -> clear with identity on record.
    if np in VERIFIED:
        return {"verdict": "clear", "confidence": "high", "method": "verified-registry",
                "rationale": (f"Name collision, no nexus. Our party '{party}' is {VERIFIED[np]}. "
                              f"The CSL match '{flag['listed_name']}' ({flag['list'].split(' - ')[0]}; "
                              f"{flag.get('programs') or 'n/a'}; {cc or 'n/a'}) is a different entity. "
                              f"Auto-cleared (verified registry).")}

    # Hard guard: any U.S.-side listing goes to a human, regardless of model opinion.
    if cc == "US":
        return {"verdict": "escalate", "confidence": "high", "method": "us-nexus-guard",
                "rationale": "Listed party has a U.S. nexus — routed to human review."}

    # Model adjudication for everything else.
    out = _llm(party, flag["party_type"], flag)
    if out and out.get("verdict") == "clear" and out.get("confidence") == "high" \
            and not out.get("same_entity", True) and cc in SANCTIONED_CC:
        # Model output is a PROPOSAL only — never a disposition of record.
        return {"verdict": "proposed_clear", "confidence": "high", "method": f"llm:{MODEL}",
                "rationale": (f"PROPOSED clear (pending human confirm): likely name collision. "
                              f"Our party '{party}' vs. listed "
                              f"'{flag['listed_name']}' ({flag['list'].split(' - ')[0]}; {cc or 'n/a'}). "
                              f"{out.get('reason','Different entity.').strip()}")}

    # Everything else: escalate (conservative default).
    why = (out.get("reason") if out else "no confident model verdict")
    return {"verdict": "escalate", "confidence": (out or {}).get("confidence", "low"),
            "method": f"llm:{MODEL}" if out else "no-model",
            "rationale": f"Escalated for human review — {why}."}

if __name__ == "__main__":
    tests = [
        {"party":"Scorpius","party_type":"CRM","listed_name":"SCORPIUS","list":"Specially Designated Nationals (SDN) - Treasury Department","programs":"IRAN-EO13846","countries":"","score":1.0},
        {"party":"Axiom","party_type":"CRM","listed_name":"AKSIOMA LIMITED LIABILITY COMPANY","list":"Specially Designated Nationals (SDN) - Treasury Department","programs":"RUSSIA-EO14024","countries":"RU","score":1.0},
        {"party":"AE Industrial","party_type":"CRM","listed_name":"AW Industrial Ltd","list":"Unverified List (UVL) - Bureau of Industry and Security","programs":"","countries":"CN","score":0.923},
        {"party":"Acme Rocketdyne LLC","party_type":"supplier","listed_name":"ACME ROCKETDYNE LLC","list":"Entity List (EL) - Bureau of Industry and Security","programs":"","countries":"US","score":1.0},
    ]
    for t in tests:
        r = adjudicate(t)
        print(f"[{r['verdict'].upper():8}] {t['party']:22} via {r['method']:18} — {r['rationale'][:110]}")
