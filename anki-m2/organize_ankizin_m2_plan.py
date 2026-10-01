#!/usr/bin/env python3
"""Teilt ein Ankizin-Deck (.apkg) in Semesterbloecke fuer die langfristige M2-Vorbereitung ein.

- Deckstruktur von Ankizin bleibt unveraendert (wichtig fuer AnkiHub-Kompatibilitaet).
- Neue Tags: M2Plan::Block_<n>_<Name> und M2Plan::Yield_<1-4> (Kurzform der Ankizin-IMPP-Relevanz).
- Reihenfolge neuer Karten: erst alle Yield-1/2-Karten (nach Block), danach Yield 3 (nach Block).
  Innerhalb dessen nach Ankizin-Lerntag-Reihenfolge -> beim Freischalten eines neuen Blocks
  kommen dessen wichtigste Karten vor liegengebliebenen Yield-3-Karten des alten Blocks.
- Aktiv: nur der Startblock (Yield 1-3). Alles andere ist ausgesetzt, nichts wird geloescht.
  Yield 4 (verzichtbar) und M1_Vorklinik bleiben dauerhaft ausgesetzt.

Nutzung: python3 organize_ankizin_m2_plan.py input.apkg output.apkg [startblock=1]
"""
import collections, json, os, re, shutil, sqlite3, sys, tempfile, time, zipfile

BLOCKS = {
    1: ("Innere", ["Innere_Medizin", "Infektiologie_und_Hygiene"]),
    2: ("Pharma_Neuro_Psych_Notfall", ["Pharmakologie", "Neurologie", "Psychiatrie", "Anästhesie",
                                       "Intensiv-_und_Notfallmedizin"]),
    3: ("Paed_Gyn_Derma_Uro", ["Pädiatrie", "Humangenetik", "Gynäkologie_und_Geburtshilfe",
                               "Dermatologie", "Urologie"]),
    4: ("Chirurgie_HNO_Auge_Radio", ["Chirurgie", "HNO", "Augenheilkunde", "Radiologie"]),
    5: ("Querschnitt", ["Arbeits-_und_Umweltmedizin", "Rechtsmedizin", "Pathologie", "Epidemiologie",
                        "Sozialmedizin", "Alternative_Heilverfahren_und_Rehabilitation",
                        "Klinische_Chemie,_Laboratoriumsdiagnostik"]),
}
BLOCK_OF_FACH = {f: b for b, (_, faecher) in BLOCKS.items() for f in faecher}
YIELD_RE = re.compile(r"M2_IMPP-Relevanz_\(yield\)::0(\d)")
LERNTAG_RE = re.compile(r"M2_Lerntag_(\d{3})")


def block_for(deck_name):
    parts = deck_name.split("::")
    if "M2_M3_Klinik" in parts:
        i = parts.index("M2_M3_Klinik")
        if i + 1 < len(parts):
            return BLOCK_OF_FACH.get(parts[i + 1])
    return None


def main(src, dst, start_block=1):
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(src) as z:
        z.extractall(tmp)
    c = sqlite3.connect(os.path.join(tmp, "collection.anki21"))
    now = int(time.time())
    decks = {int(k): v["name"] for k, v in json.loads(c.execute("select decks from col").fetchone()[0]).items()}

    note_block = {}
    for nid, did in c.execute("select nid, did from cards"):
        note_block.setdefault(nid, block_for(decks[did]))

    note_info = {}
    for nid, tags in c.execute("select id, tags from notes").fetchall():
        y = YIELD_RE.search(tags)
        yld = int(y.group(1)) if y else None
        lt = [int(x) for x in LERNTAG_RE.findall(tags)]
        block = note_block.get(nid)
        new = [t for t in tags.split() if not t.startswith("M2Plan::")]
        if block:
            new.append(f"M2Plan::Block_{block}_{BLOCKS[block][0]}")
        if yld:
            new.append(f"M2Plan::Yield_{yld}")
        c.execute("update notes set tags=?, mod=?, usn=-1 where id=?", (" " + " ".join(new) + " ", now, nid))
        note_info[nid] = (block, yld, min(lt) if lt else 999)

    stats = collections.Counter()
    cards = c.execute("select id, nid, ord, due from cards").fetchall()

    def sort_key(card):
        cid, nid, ord_, due = card
        block, yld, lerntag = note_info[nid]
        tier = 0 if yld in (1, 2) else 1
        return (block is None, tier, block or 9, yld or 9, lerntag, nid, ord_)

    for pos, (cid, nid, ord_, due) in enumerate(sorted(cards, key=sort_key), start=1):
        block, yld, _ = note_info[nid]
        active = block == start_block and yld in (1, 2, 3)
        c.execute("update cards set due=?, queue=?, mod=?, usn=-1 where id=? and type=0",
                  (pos, 0 if active else -1, now, cid))
        stats[(block, yld, active)] += 1
    c.commit()
    c.execute("vacuum")
    c.close()

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for name in os.listdir(tmp):
            z.write(os.path.join(tmp, name), name)
    shutil.rmtree(tmp)

    print("Block | Yield1 Yield2 Yield3 Yield4 | aktiv")
    for b in [*BLOCKS, None]:
        row = [sum(n for (bb, y, _), n in stats.items() if bb == b and y == yy) for yy in (1, 2, 3, 4)]
        act = sum(n for (bb, _, a), n in stats.items() if bb == b and a)
        print(f"{b!s:5} | {row[0]:6} {row[1]:6} {row[2]:6} {row[3]:6} | {act}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
