# Anki-Organisation für das M2

## Aktuell: Ankizin-Semesterplan (`organize_ankizin_m2_plan.py`)

Das Skript teilt das Ankizin-Deck (`amboss_decks.apkg`, 33.893 Karten) in 5 Semesterblöcke ein:
`M2Plan::Block_1_Innere` … `Block_5_Querschnitt`, dazu `M2Plan::Yield_1–4` (aus der IMPP-Relevanz von Ankizin).
Aktiv ist nur Block 1 mit Yield 1–3. Yield 4 und M1_Vorklinik bleiben ausgesetzt.
Die neuen Karten sind sortiert: zuerst alle Yield-1/2-Karten nach Block, dann Yield 3, jeweils in der Reihenfolge der AMBOSS-Lerntage.

```
python3 organize_ankizin_m2_plan.py amboss_decks.apkg M2_Ankizin_Semesterplan.apkg [startblock]
```

| Block | Zeitraum | Fächer | Yield 1–2 | Yield 3 |
|---|---|---|---|---|
| 1 | WiSe 26/27 | Innere, Infektiologie | 1.937 | 5.237 |
| 2 | SoSe 27 | Pharma, Neuro, Psych, Anästhesie, Notfall | 1.973 | 5.084 |
| 3 | WiSe 27/28 | Päd, Gyn, Humangenetik, Derma, Uro | 1.393 | 4.978 |
| 4 | SoSe 28 | Chirurgie, Ortho, HNO, Auge, Radio | 1.862 | 5.263 |
| 5 | Okt–Dez 28 | Rechtsmed, Arbeits-/Sozialmed, Patho, Epi | 661 | 1.742 |

Pensum: 20 neue Karten pro Tag, sonntags nur Wiederholungen. Gekreuzt wird einmal pro Woche (30–40 IMPP-Fragen), einmal im Monat gemischt (80 Fragen) und am Ende jedes Blocks als Blockklausur.

---

## Älter: Ankiphil Vorklinik

## Befund zum hochgeladenen Deck (`amboss_neu_ohne_bilder.apkg`)

- Inhalt: **Ankiphil Vorklinik v6.0** (Physikum-Stoff), 4.902 Notizen / 8.424 Karten. Kein M2-Deck.
- Alle Karten sind neu (keine Lernhistorie im Export).
- Bilder wurden nicht mitexportiert: 176 Image-Occlusion-Notizen sind ohne Bild unbrauchbar,
  bei ~2.100 Cloze-Notizen fehlt nur das Zusatzbild auf der Rückseite.

## Was `reorganize_vorklinik_for_m2.py` macht

- Alle Karten liegen in **einem** Deck `M2::Vorklinik-Grundlagen`. Die Fächer stehen als Tags dran, nicht als Unterdecks.
- Neue Tags: `M2::Fach::<Fach>`, `M2::Prio::1_Klinik | 2_HighYield | 3_Archiv`, `M2::Bild_fehlt`.
- **Aktiv (2.007 Karten):** klinisch relevante Karten (Ankiphil-Tag `§Klinik_Relevanz` oder ausgefülltes
  Feld „Klinik“) aus Anatomie, Physiologie, Biochemie, Biologie, Psych/Soz sowie High-Yield aus Physio und Biochemie.
- **Ausgesetzt, nicht gelöscht (6.417 Karten):** Terminologie, Physik, Chemie, Image Occlusion und reines Detailwissen.

```
python3 reorganize_vorklinik_for_m2.py amboss_neu_ohne_bilder.apkg M2_Vorklinik-Grundlagen.apkg
```

## Import

1. Altes Deck „amboss neu“ in Anki löschen. Es hat keine Lernhistorie, du verlierst also nichts.
   Sonst behält Anki beim Import die alte Deckzuordnung.
2. `M2_Vorklinik-Grundlagen.apkg` importieren.
3. Unter Optionen FSRS aktivieren und die gewünschte Behaltensrate auf 0,85–0,90 setzen.

## Lernstrategie fürs M2

Dieses Deck liefert nur die **Grundlagen**. Den Großteil der M2-Punkte holst du mit klinischem Stoff:

- **Hauptquelle:** Amboss-Kreuzplan bzw. IMPP-Altfragen. Anki nutzt du ergänzend, um Fehler aus den Kreuzsitzungen
  festzuhalten: Zu jeder falsch gekreuzten Frage schreibst du 1–2 eigene Karten mit dem Tag `M2::Fach::...`.
- **Klinisches Anki-Deck:** Ein M2-Deck (z. B. Ankiphil Klinik) dazunehmen und mit derselben Tag-Logik
  (`M2::Fach::Innere::Kardio` usw.) unter dem Deck `M2` einsortieren.
- **Reihenfolge der Fächer:** Innere (Kardio, Pneumo, Gastro, Endo, Nephro, Häm/Onko, Infektio), Neuro,
  Pädiatrie, Gyn, Chirurgie, Pharmakologie, Allgemeinmedizin, Psychiatrie und dann die kleinen Fächer.
- **Tagespensum:** Neue Karten pro Tag = verbleibende Karten ÷ (Tage bis zur Prüfung − 14). In den letzten zwei Wochen keine neuen Karten mehr, nur Wiederholungen.
- **Leeches** (nach 6–8 Fehlversuchen) neu formulieren oder aussetzen, statt sie weiter zu wiederholen.
