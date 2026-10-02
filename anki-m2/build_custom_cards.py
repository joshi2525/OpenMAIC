#!/usr/bin/env python3
"""Baut aus einer Kartendatei (anki-m2/cards/<thema>.py) ein importierbares .apkg.

Nutzung: python3 build_custom_cards.py cards/cyp450.py "M2 Lernplan::1 Sem5 Pharma-Push::00 CYP450-System" CYP450 out.apkg
Benötigt: pip install anki
"""
import importlib.util, os, sys, tempfile
from anki.collection import Collection, ExportAnkiPackageOptions, DeckIdLimit

CSS = """.card{font-family:"Source Sans 3","Segoe UI",system-ui,sans-serif;font-size:21px;line-height:1.45;text-align:left;
color:#14262b;background:#f6f9f9;max-width:720px;margin:0 auto;padding:8px 4px}
.nightMode .card,.card.nightMode{color:#e3eded;background:#0e1a1d}
.cloze{font-weight:700;color:#1f6f78}.nightMode .cloze{color:#5fb7bf}
.extra{margin-top:18px;padding-top:12px;border-top:1px solid #c9d8d9;font-size:17px;color:#40565b}
.nightMode .extra{border-color:#2a3d42;color:#a9bcc0}
.extra table{border-collapse:collapse;margin-top:6px}.extra td,.extra th{border:1px solid #c9d8d9;padding:4px 8px;text-align:left}
.tag{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#1f6f78;margin-bottom:10px}"""


def main(cards_py, deck_root, tag, out):
    spec = importlib.util.spec_from_file_location("cards", cards_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tmp = tempfile.mkdtemp()
    col = Collection(os.path.join(tmp, "c.anki2"))
    mm = col.models
    m = mm.new("M2 Lückentext")
    m["type"] = 1  # Cloze
    for f in ("Text", "Extra"):
        mm.add_field(m, mm.new_field(f))
    t = mm.new_template("Lückentext")
    t["qfmt"] = '<div class="tag">{{Subdeck}}</div>{{cloze:Text}}'
    t["afmt"] = '<div class="tag">{{Subdeck}}</div>{{cloze:Text}}{{#Extra}}<div class="extra">{{Extra}}</div>{{/Extra}}'
    mm.add_template(m, t)
    m["css"] = CSS
    mm.add(m)
    m = mm.by_name("M2 Lückentext")
    root_id = col.decks.id(deck_root)
    n_notes = n_cards = 0
    for section, cards in mod.SECTIONS:
        did = col.decks.id(f"{deck_root}::{section}")
        for text, extra in cards:
            note = col.new_note(m)
            note["Text"], note["Extra"] = text, extra
            note.tags = [f"M2Plan::{tag}", f"M2Plan::{tag}::{section.split(' ', 1)[1].replace(' ', '_')}"]
            col.add_note(note, did)
            n_notes += 1
            n_cards += len(note.cards())
    col.export_anki_package(out_path=os.path.abspath(out),
                            options=ExportAnkiPackageOptions(with_scheduling=False, with_deck_configs=False, with_media=True, legacy=False),
                            limit=DeckIdLimit(root_id))
    col.close()
    print(f"{n_notes} Notizen, {n_cards} Karten -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
