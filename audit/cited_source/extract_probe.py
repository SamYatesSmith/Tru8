"""Free offline test: can cited-source names be read mechanically from a pool?

Patterns over non-primary items' text (verbatim first, else snippet):
  according to (the) X | X said/announced/reported/found/estimated/published
  a (new) X analysis/report/study/survey/review | data/figures (collected) by/from X
  revealed in/by X | wrote in X | X's (analysis|report|data|figures)
X = a capitalised name (1-6 words, connectors of/for/and/the allowed) or an
acronym. Names are counted by the number of DISTINCT items citing them.
Run from backend/:  PYTHONPATH=. python ../audit/cited_source/extract_probe.py PROD_RAW
"""

import base64, gzip, json, re, sys
from collections import Counter

NAME = r"((?:[A-Z][\w&'’.-]*|[A-Z]{2,})(?:\s+(?:of|for|and|the|on|[A-Z][\w&'’.-]*|[A-Z]{2,})){0,5})"
PATTERNS = [
    r"according to (?:the |a |an )?(?:new |latest |recent )?" + NAME,
    NAME
    + r"(?:'s|’s)? (?:said|announced|reported|found|estimated|published|confirmed|revealed|showed|data|figures|analysis|report)",
    r"\b(?:a|an|the) (?:new |latest |recent )?"
    + NAME
    + r" (?:analysis|report|study|survey|review|investigation|release|bulletin|estimate)",
    r"(?:data|figures|statistics|numbers) (?:collected |published |released )?(?:by|from) (?:the )?"
    + NAME,
    r"(?:revealed|reported|first reported|published) (?:in|by) (?:the )?" + NAME,
    r"wrote in (?:the )?" + NAME,
    r"(?:citing|cited) (?:the )?" + NAME,
]
RX = [re.compile(p) for p in PATTERNS]
GENERIC = set(
    "The This That It He She They We I A An In On At For But And Mr Mrs Ms Dr However Meanwhile According Reuters AP AFP".split()
)


def names(text):
    out = set()
    for rx in RX:
        for m in rx.finditer(text or ""):
            n = m.group(1).strip(" .,'’")
            words = n.split()
            while words and words[0] in GENERIC:
                words = words[1:]
            n = " ".join(words)
            if len(n) >= 3 and not n.isdigit():
                out.add(n)
    return out


raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
pools = json.loads(
    gzip.decompress(
        base64.b64decode(raw.split("@@BEGIN@@", 1)[1].split("@@END@@", 1)[0])
    )
)
latest = {}
for cid, p in sorted(pools.items(), key=lambda kv: kv[1]["created"], reverse=True):
    latest.setdefault((p["claim"] or "").strip().lower(), cid)

TARGETS = {
    "Delo": "#1",
    "Innovation Center": "#2",
    "Saxony-Anhalt": "#4",
    "28,700": "#6",
    "Sussex": "#15",
    "quietest": "#17",
}
per_pool = []
for key, cid in latest.items():
    p = pools[cid]
    c = Counter()
    for it in p["items"]:
        if it.get("tier") == "primary":
            continue
        for n in names(it.get("verbatim") or it.get("text") or ""):
            c[n] += 1
    tag = next(
        (v for k, v in TARGETS.items() if k.lower() in (p["claim"] or "").lower()), ""
    )
    per_pool.append((tag, p["claim"][:90], c))
for tag, claim, c in sorted(per_pool, key=lambda x: (x[0] == "", x[1])):
    top = [(n, k) for n, k in c.most_common(8) if k >= 2]
    print(f"{tag or '  '} {claim}\n     >=2 items: {top}")
print(
    "\npools",
    len(per_pool),
    "| pools with any name cited by >=2 items:",
    sum(1 for _, _, c in per_pool if any(k >= 2 for k in c.values())),
)
