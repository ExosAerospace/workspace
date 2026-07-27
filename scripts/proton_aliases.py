"""Canonical map of Jon's Proton mailbox aliases — single source of truth.

All four Proton aliases below land in ONE mailbox (served by the Bridge on
127.0.0.1:1143 / :1025), so any intake / self-send / BCC detection must treat
them interchangeably. The IMAP scripts previously each hardcoded a *different
partial* set, which had already drifted (some missing jquinnexo@proton.me,
others missing the exosmc variants). Import from here instead of re-listing.

Two identities, each with a .pm.me and .proton.me face:
  - jquinnexo  -> Jon's personal alias (DEFAULT); BCC intake for submissions
                  archive, sent-loop-closer, MC email tracker
  - exosmc     -> ops / email command channel (@Exobot / [EXO] tasking)
"""

# The four Proton aliases on Jon's account (all -> same inbox)
PROTON_ALIASES = frozenset({
    "jquinnexo@pm.me",
    "jquinnexo@proton.me",
    "exosmc@pm.me",
    "exosmc@proton.me",
})

# Plus-addressing variants used by the email command channel
COMMAND_ALIASES = frozenset({
    "jquinnexo+do@pm.me",
    "exosmc+do@proton.me",
})

# Jon's work identity (separate mail system, but counts as "self")
WORK_ADDRS = frozenset({"jquinn@exosaero.com"})

# Domains that count as self (for substring/domain-style matching)
SELF_DOMAINS = frozenset({"exosaero.com"})

# Everything that counts as "self / Jon" for self-send + intake detection
SELF_ADDRS = PROTON_ALIASES | WORK_ADDRS


def is_self(addr):
    """True if an email address belongs to Jon (any Proton alias, +tag variant,
    or work address / domain). Accepts bare addresses or 'Name <addr>' form."""
    if not addr:
        return False
    a = addr.strip().lower()
    if "<" in a and ">" in a:
        a = a[a.rfind("<") + 1:a.rfind(">")].strip()
    if a in SELF_ADDRS or a in COMMAND_ALIASES:
        return True
    if "+" in a and "@" in a:                      # strip +tag, retry base
        local, dom = a.split("@", 1)
        if local.split("+", 1)[0] + "@" + dom in SELF_ADDRS:
            return True
    return a.split("@")[-1] in SELF_DOMAINS
