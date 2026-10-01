#!/usr/bin/env python3
"""Baut aus einem Ankizin-Export (.apkg) ein Deck "M2 Lernplan" mit kleinschrittigen Unterdecks.

Struktur (Nummern legen die Reihenfolge in Anki fest):
  M2 Lernplan::1 Sem5 Pharma-Push::<Modul>::<NN Thema>
  M2 Lernplan::2 Sem5 Modul Hormonsystem::<Fach>::<NN Thema>    (analog 3 Sinnessysteme, 4 Notfall II)
  M2 Lernplan::5 Spaeter nach Fach::<Fach>::<NN Thema>
  M2 Lernplan::6 Vorklinik, 9 Verzichtbar (Yield 4), 0 Infos
Themen = AMBOSS-Lerntag-Themen aus den Ankizin-Tags. Innerhalb eines Themas: Yield 1 -> 2 -> 3.

Alle Notizen/Karten bekommen neue IDs und GUIDs, damit Anki sie beim Import als neue Karten anlegt
(ein Import ueber bereits vorhandene Karten aendert deren Deck nicht). Vorher das alte Deck loeschen.

Nutzung: python3 build_m2_lernplan_deck.py amboss_decks.apkg M2_Lernplan.apkg
"""
import collections, json, os, re, secrets, shutil, sqlite3, sys, tempfile, time, zipfile

ROOT = "M2 Lernplan"
PHARMA_MODULE = [  # (Unterdeck, Pharma-Lerntage)
    ("1 Hormonsystem-Pharma", {"076"}),
    ("2 Sinnessysteme-Pharma", {"077"}),
    ("3 Notfall II-Pharma", {"074", "075"}),
    ("4 Rest-Pharma", None),
]
SEM5_MODULE = [  # (Deck, [(Fach-Unterdeck, Ankizin-Fachdeck)])
    ("2 Sem5 Modul Hormonsystem", [("1 Endokrinologie", "Endokrinologie_und_Stoffwechsel"),
                                   ("2 Gynäkologie und Geburtshilfe", "Gynäkologie_und_Geburtshilfe"),
                                   ("3 Urologie", "Urologie")]),
    ("3 Sem5 Modul Sinnessysteme", [("1 Augenheilkunde", "Augenheilkunde"), ("2 HNO", "HNO")]),
    ("4 Sem5 Modul Notfall II", [("1 Anästhesie", "Anästhesie"),
                                 ("2 Intensiv- und Notfallmedizin", "Intensiv-_und_Notfallmedizin")]),
]
SPAETER = [  # Reihenfolge der restlichen Faecher
    "Kardiologie_und_Angiologie", "Pneumologie", "Gastroenterologie", "Nephrologie",
    "Hämatologie_und_Onkologie", "Rheumatologie", "Infektiologie_und_Hygiene", "Neurologie", "Psychiatrie",
    "Pädiatrie", "Humangenetik", "Dermatologie", "Viszeralchirurgie", "Unfallchirurgie", "Orthopädie",
    "Allgemein-,Thorax-_und_Gefäßchirurgie", "Radiologie", "Pathologie", "Rechtsmedizin",
    "Arbeits-_und_Umweltmedizin", "Sozialmedizin", "Epidemiologie", "Klinische_Chemie,_Laboratoriumsdiagnostik",
    "Alternative_Heilverfahren_und_Rehabilitation",
]
MIN_TOPIC = 5  # kleinere Themen landen in "Weitere Themen"
LERNTAG_RE = re.compile(r"M2_Lerntag_(\d{3})_([^:\s]+)::([^:\s]+)")
PHARMA_LIB_RE = re.compile(r"Bibliothek-Klinik::Pharmakologie::([^:\s]+)")
YIELD_RE = re.compile(r"M2_IMPP-Relevanz_\(yield\)::0(\d)")


def pretty(s):
    return s.replace("_", " ").replace("::", " ").strip()


def fach_of(deck):
    p = deck.split("::")
    if "M2_M3_Klinik" not in p:
        return "Vorklinik" if "M1_Vorklinik" in p else None
    i = p.index("M2_M3_Klinik")
    rest = p[i + 1:]
    if rest and rest[0] in ("Innere_Medizin", "Chirurgie") and len(rest) > 1:
        return rest[1]
    return rest[0] if rest else None


def topic_of(tags, fach):
    hits = sorted(set(LERNTAG_RE.findall(tags)))
    if not hits:
        return None, "999"
    key = fach[:6].lower()
    own = [h for h in hits if h[1][:6].lower() == key]
    lt, _, topic = (own or hits)[0]
    return topic, lt


def main(src, dst):
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(src) as z:
        z.extractall(tmp)
    c = sqlite3.connect(os.path.join(tmp, "collection.anki21"))
    decks = json.loads(c.execute("select decks from col").fetchone()[0])
    names = {int(k): v["name"] for k, v in decks.items()}
    template = next(v for v in decks.values() if v["id"] != 1)

    note_deck = {}
    for nid, did in c.execute("select nid, did from cards"):
        note_deck.setdefault(nid, names[did])

    # 1) Jede Notiz einem Pfad zuordnen: (Hauptdeck, Unterdeck, Lerntag, Thema)
    placement, yields = {}, {}
    for nid, tags in c.execute("select id, tags from notes").fetchall():
        fach = fach_of(note_deck[nid])
        y = YIELD_RE.search(tags)
        yld = int(y.group(1)) if y else 3
        yields[nid] = yld
        if fach is None:
            own = None if "Ankizin" in note_deck[nid] else note_deck[nid]  # eigene Decks bleiben, wie sie sind
            placement[nid] = (own or "0 Infos", None, "000", None)
            continue
        if fach == "Vorklinik":
            placement[nid] = ("6 Vorklinik (M1)", None, "000", None)
            continue
        if yld == 4:
            placement[nid] = ("9 Verzichtbar (Yield 4)", pretty(fach), "000", None)
            continue
        topic, lt = topic_of(tags, fach)
        if fach == "Pharmakologie":
            pharma_lt = sorted(set(x[0] for x in LERNTAG_RE.findall(tags) if x[1] == "Pharmakologie"))
            lt_p = pharma_lt[0] if pharma_lt else None
            if lt_p:
                topic = next(x[2] for x in sorted(LERNTAG_RE.findall(tags)) if x[0] == lt_p)
                lt = lt_p
            else:  # ohne Pharma-Lerntag: Wirkstoffgruppe aus der AMBOSS-Bibliothek
                lib = PHARMA_LIB_RE.search(tags)
                topic, lt = (f"Weitere {lib.group(1)}" if lib else None), "998"
            sub = next((n for n, lts in PHARMA_MODULE if lts and lt_p in lts), "4 Rest-Pharma")
            placement[nid] = ("1 Sem5 Pharma-Push", sub, lt, topic)
            continue
        main_deck = sub = None
        for mod, faecher in SEM5_MODULE:
            for label, f in faecher:
                if f == fach:
                    main_deck, sub = mod, label
        if main_deck is None:
            idx = SPAETER.index(fach) + 1 if fach in SPAETER else 99
            main_deck, sub = "5 Später nach Fach", f"{idx:02d} {pretty(fach)}"
        placement[nid] = (main_deck, sub, lt, topic)

    # 2) Kleine Themen zusammenfassen, Themen nummerieren (nach Lerntag-Reihenfolge)
    size = collections.Counter((p[0], p[1], p[3]) for p in placement.values() if p[3])
    first_lt = {}
    for p in placement.values():
        if p[3]:
            k = (p[0], p[1], p[3])
            first_lt[k] = min(first_lt.get(k, "999"), p[2])
    numbering = {}
    for parent in sorted(set(k[:2] for k in size)):
        topics = sorted((k for k in size if k[:2] == parent and size[k] >= MIN_TOPIC),
                        key=lambda k: (first_lt[k], k[2]))
        for i, k in enumerate(topics, 1):
            numbering[k] = f"{i:02d} {pretty(k[2])}"
    deck_path = {}
    for nid, (m, sub, lt, topic) in placement.items():
        if "::" in m or not m[0].isdigit():
            deck_path[nid] = m
            continue
        parts = [ROOT, m] + ([sub] if sub else [])
        if m not in ("0 Infos", "6 Vorklinik (M1)", "9 Verzichtbar (Yield 4)"):
            parts.append(numbering.get((m, sub, topic), "99 Weitere Themen"))
        deck_path[nid] = "::".join(parts)

    # 3) Decks anlegen (inkl. aller Elterndecks)
    now = int(time.time())
    all_paths = set()
    for path in deck_path.values():
        p = path.split("::")
        for i in range(1, len(p) + 1):
            all_paths.add("::".join(p[:i]))
    new_decks = {"1": decks["1"]}
    path_id = {}
    for i, path in enumerate(sorted(all_paths)):
        did = now * 1000 + i
        d = json.loads(json.dumps(template))
        d.update(id=did, name=path, mod=now, usn=-1, desc="", conf=1)
        new_decks[str(did)] = d
        path_id[path] = did

    # 4) Neue IDs/GUIDs, Tags bereinigen, Karten einsortieren, Reihenfolge setzen
    base_n, base_c = now * 1000 + 10_000_000, now * 1000 + 20_000_000
    old_notes = c.execute("select id from notes order by id").fetchall()
    nid_map = {old: base_n + i for i, (old,) in enumerate(old_notes)}
    for old, new in nid_map.items():
        tags = c.execute("select tags from notes where id=?", (old,)).fetchone()[0]
        tags = " ".join(t for t in tags.split() if not t.startswith("AnkiHub_Subdeck"))
        c.execute("update notes set id=?, guid=?, tags=?, mod=?, usn=-1 where id=?",
                  (new, secrets.token_hex(8), f" {tags} ", now, old))

    cards = c.execute("select id, nid, ord from cards").fetchall()
    cards.sort(key=lambda r: (deck_path[r[1]], yields[r[1]], r[1], r[2]))
    for pos, (cid, nid, ord_) in enumerate(cards, 1):
        c.execute("update cards set id=?, nid=?, did=?, odid=0, odue=0, type=0, queue=0, due=?, ivl=0, "
                  "factor=0, reps=0, lapses=0, left=0, mod=?, usn=-1 where id=?",
                  (base_c + pos, nid_map[nid], path_id[deck_path[nid]], pos, now, cid))
    c.execute("delete from graves")
    c.execute("delete from revlog")
    c.execute("update col set decks=?, mod=?", (json.dumps(new_decks), now * 1000))
    c.commit()
    stats = collections.Counter(deck_path[nid].split("::")[1] for _, nid, _ in cards)
    c.execute("vacuum")
    c.close()

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for name in os.listdir(tmp):
            z.write(os.path.join(tmp, name), name)
    shutil.rmtree(tmp)
    print(f"{len(all_paths)} Decks, {len(cards)} Karten")
    for k in sorted(stats):
        print(f"  {k:32s} {stats[k]:6d}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
