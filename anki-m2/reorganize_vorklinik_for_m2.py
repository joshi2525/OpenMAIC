#!/usr/bin/env python3
"""Reorganisiert ein Ankiphil-Vorklinik-Deck (.apkg) fuer die M2-Vorbereitung.

- Alle Karten landen in einem Deck "M2::Vorklinik-Grundlagen" (Faecher als Tags statt Unterdecks).
- Tags: M2::Fach::<Fach>, M2::Prio::1_Klinik | 2_HighYield | 3_Archiv, M2::Bild_fehlt
- Aktiv bleiben nur klinisch relevante Karten (plus Physio/Biochemie High-Yield),
  alles andere wird ausgesetzt (suspended) - nichts wird geloescht.

Nutzung: python3 reorganize_vorklinik_for_m2.py input.apkg output.apkg
"""
import json, os, shutil, sqlite3, sys, tempfile, time, zipfile, collections

ROOT_DECK = "M2"
TARGET_DECK = "M2::Vorklinik-Grundlagen"
FACH_BY_DECK = {  # Deckname-Bestandteil -> Fach-Tag
    "Anatomie": "Anatomie", "Physiologie": "Physiologie", "Biochemie": "Biochemie",
    "Biologie": "Biologie", "Chemie": "Chemie", "Physik": "Physik",
    "Psychologie & Soziologie": "Psych_Soz", "Medizinische Terminologie": "Terminologie",
}
KLINIK_FAECHER = {"Anatomie", "Physiologie", "Biochemie", "Biologie", "Psych_Soz"}
HY_FAECHER = {"Physiologie", "Biochemie"}  # Grundlagen, die im M2 (Innere/Pharma) staendig gebraucht werden


def fach_for(deck_name):
    for part in deck_name.split("::"):
        if part in FACH_BY_DECK:
            return FACH_BY_DECK[part]
    return "Sonstiges"


def main(src, dst):
    tmp = tempfile.mkdtemp()
    with zipfile.ZipFile(src) as z:
        z.extractall(tmp)
    db = os.path.join(tmp, "collection.anki21")
    c = sqlite3.connect(db)
    now = int(time.time())

    decks, models = (json.loads(x) for x in c.execute("select decks, models from col").fetchone())
    deck_names = {int(k): v["name"] for k, v in decks.items()}
    models = {int(k): v for k, v in models.items()}

    # Neue Deckstruktur: Default + M2 + M2::Vorklinik-Grundlagen
    template = next(v for v in decks.values() if v["id"] != 1)
    root_id, target_id = now * 1000, now * 1000 + 1
    new_decks = {"1": decks["1"]} if "1" in decks else {}
    for did, name in ((root_id, ROOT_DECK), (target_id, TARGET_DECK)):
        d = json.loads(json.dumps(template))
        d.update(id=did, name=name, mod=now, usn=-1, desc="")
        new_decks[str(did)] = d

    note_fach = {}
    for nid, did in c.execute("select nid, did from cards"):
        note_fach.setdefault(nid, fach_for(deck_names.get(did, "")))

    stats = collections.Counter()
    active_notes = set()
    for nid, mid, flds, tags in c.execute("select id, mid, flds, tags from notes").fetchall():
        m = models[mid]
        f = dict(zip([x["name"] for x in m["flds"]], flds.split("\x1f")))
        fach = note_fach.get(nid, "Sonstiges")
        klinik = "§Klinik_Relevanz" in tags or f.get("Klinik", "").strip() != ""
        hy = "!High-Yield" in tags
        occlusion = "iOcclusion" in m["name"]
        bild_fehlt = occlusion or "<img" in f.get("Text", "")

        if klinik and fach in KLINIK_FAECHER and not occlusion:
            prio, active = "1_Klinik", True
        elif hy and fach in HY_FAECHER and not occlusion:
            prio, active = "2_HighYield", True
        else:
            prio, active = "3_Archiv", False

        new = [t for t in tags.split() if not t.startswith("M2::")]
        new += [f"M2::Fach::{fach}", f"M2::Prio::{prio}"]
        if bild_fehlt:
            new.append("M2::Bild_fehlt")
        c.execute("update notes set tags=?, mod=?, usn=-1 where id=?", (" " + " ".join(new) + " ", now, nid))
        if active:
            active_notes.add(nid)
        stats[(fach, prio)] += 1

    for cid, nid in c.execute("select id, nid from cards").fetchall():
        queue = 0 if nid in active_notes else -1
        c.execute("update cards set did=?, queue=?, mod=?, usn=-1 where id=?", (target_id, queue, now, cid))

    c.execute("update col set decks=?, mod=?", (json.dumps(new_decks), now * 1000))
    c.commit()
    active_cards = c.execute("select count(*) from cards where queue=0").fetchone()[0]
    total_cards = c.execute("select count(*) from cards").fetchone()[0]
    c.execute("vacuum")
    c.close()

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for name in os.listdir(tmp):
            z.write(os.path.join(tmp, name), name)
    shutil.rmtree(tmp)

    print(f"Aktive Karten: {active_cards} / {total_cards}")
    for (fach, prio), n in sorted(stats.items()):
        print(f"  {fach:14s} {prio:12s} {n:5d} Notizen")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
