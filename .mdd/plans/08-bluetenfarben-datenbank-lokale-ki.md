# Plan — Die Blütenfarben-Datenbank: lokale KI-Pipeline auf offenen Bildern

> Ausführungsplan für Teil 1 von `.mdd/plans/02-bluetenfarben-und-textextraktion.md`,
> in der Tiefe, die zum Bauen reicht: Quellen mit geprüften API-Aufrufen,
> Modelle mit Lizenz und Laufzeit **auf dieser Maschine** (Apple M1, 16 GB, kein
> torch/mlx/ollama installiert — gemessen), die Farbmetrik mit Formeln und
> Schwellen, das VLM-Schema, die Aggregationsregeln, das Provenienz-Schema, die
> Tests, die Budgets. Alles am 2026-09-07 gegen echte Endpunkte geprüft, wo es
> „geprüft" heißt.
>
> **Der Befund, der den Plan rechtfertigt:** von den ~4 300 Kernarten haben
> 590 eine GIFT-Farbe. **1 222 insektenbestäubte Kernarten haben keine** —
> darunter Acker-Witwenblume, Margerite, Kornblume, Schafgarbe und
> Buschwindröschen (alle fünf geprüft: keine GIFT-Farbe). Das ist genau der
> Teil des Katalogs, für den Blühkalender und Farbpunkte gebaut sind.
>
> **Und der Befund, der ihn machbar macht:** eine Zufallsstichprobe von 20
> dieser Arten hatte **20/20** ≥ 5 offene (CC0/CC-BY) GBIF-Belegfotos weltweit,
> **19/20** ≥ 5 aus Deutschland, 14/20 ≥ 3 Commons-Dateien mit strukturiertem
> „zeigt"-Statement, 16/20 direkt per GBIF-ID auf Wikidata. Bilder sind nicht
> der Engpass. Die Arbeit ist Auswahl, Messung, Urteil und Provenienz.

---

## 0. Kurzfassung

Eine **Ingest-Zeit-Pipeline** (offline, lokal, nie im Container) sammelt je
Art bis zu zwölf lizenzklare Fotos aus vier offenen Quellen, sortiert
Herbarbelege, Zeichnungen, Blätter und Früchte aus, **findet und maskiert die
Blüte** (Grounding DINO + SAM 2, alternativ Florence-2), **misst** die Farben der
Maske in CIELAB, lässt ein **lokales VLM** (Qwen3-VL) unabhängig urteilen, holt
eine dritte Stimme aus einem **Embedding-Probe** (DINOv2 + logistische
Regression, trainiert an GIFT), **aggregiert** die Stimmen über alle Bilder einer
Art zu Primär- und Sekundärfarbe mit Konfidenz, **validiert** gegen die 524
GIFT-Farben des Kerns, legt strittige Arten einem Menschen als Kontaktbogen vor
und schreibt Werte **nur** über `upsert_trait` — mit Belegfotos, Autor und Lizenz
je Wert, damit die Seite sagen kann, woher sie es weiß.

Drei Stimmen mit verschiedenen Fehlerarten (Pixel, Sprache, Embedding) sind
der Kern des Entwurfs: jede allein irrt anders, und Uneinigkeit ist das Signal
für den Menschen.

---

## 1. Ziel und Definitionen

| Begriff | Festlegung |
|---|---|
| **Primärfarbe** | die Farbe des auffälligen Teils, den ein Gärtner „die Blüte" nennt: Kronblätter, Perigon, bei Korbblütlern die Zungen- oder Röhrenblüten, bei Wolfsmilch die Hochblätter. Nicht die Botanik entscheidet, sondern das, was auf dem Plan als Farbpunkt gemalt wird |
| **Sekundärfarbe** | eine zweite, deutlich andere Farbe, die verlässlich sichtbar ist: das gelbe Körbchen der Margerite, die Zeichnung des Stiefmütterchens, der andersfarbige Schlund. Nur wenn sie in der Mehrzahl der Bilder auftritt |
| **Variabel** | Arten mit echten Farbmorphen (Buschwindröschen weiß/rosa, Kornblume blau/rosa, Wiesen-Schaumkraut weiß/lila): beide Farben werden gespeichert, die häufigere ist primär, und ein Flag sagt, dass es eine Wahl gibt |
| **Vokabular** | die zehn zeichenbaren Farben (`DRAWABLE`, `colours.ts`): yellow, white, pink, violet, blue, red, orange, green, brown, black. Geschlossen, weil die Zeichenschicht genau diese kennt. Eine Erweiterung (purpur, creme) ist eine Entscheidung (Abschnitt 16), kein Nebeneffekt |
| **Konfidenz** | 0–1 je Art, aus Einigkeit der Stimmen × Bildmenge × Quellenvielfalt (Abschnitt 8). Steht im `trait.confidence` und auf der Seite |
| **Provenienz** | `source`, `license`, `confidence`, `retrieved_at` je Wert (`upsert_trait` wirft sonst) **plus** Belegfotos mit Autor, Lizenz und Link je Art |

**Artenmenge, in Stufen:** (1) die 1 222 insektenbestäubten Kernarten ohne
Farbe; (2) alle Kernarten ohne Farbe; (3) die GIFT-Arten *mit* Farbe — nicht
zum Überschreiben (Quellen überschreiben sich nie), sondern als Grundwahrheit
und für die Sekundärfarbe, die GIFT nicht hat; (4) der Rest der 8 939
(windbestäubte Gräser und Seggen: grün/braun, geringer Nutzen, billig).

---

## 2. Bildquellen — geprüft, mit Lizenzfeldern

| Quelle | Was sie liefert | Geprüft am 2026-09-07 | Lizenz je Bild |
|---|---|---|---|
| **Wikidata** | Brücke von unserer `taxon_id` (= GBIF-Schlüssel) zum Item: `?item wdt:P846 "<key>"` per SPARQL, in `VALUES`-Blöcken zu 200; daraus `P18` (Bild), `P373` (Commons-Kategorie), Sitelinks de/en | 16/20 Kernarten aufgelöst; Knautia → Q27648 mit P18 und P373 | — (Brücke) |
| **Commons, strukturierte Daten** | Dateien, die die Art *zeigen*: `list=search&srsearch=haswbstatement:P180=<QID>&srnamespace=6` | Knautia: **122 Dateien**; 14/20 Stichprobenarten ≥ 3 | `prop=imageinfo&iiprop=extmetadata`: `LicenseShortName`, `License`, `Artist`, `Credit`, `AttributionRequired`, `UsageTerms`; Thumbnail über `iiurlwidth=640` |
| **Commons, Kategorie** | `list=categorymembers&cmtitle=Category:<Name>&cmtype=file` — ergänzt „depicts" um unstrukturierte Dateien | Knautia: 50 Dateien | wie oben |
| **Wikipedia, Artikelbilder** | `GET /api/rest_v1/page/media-list/<Titel>` (de, dann en): alle Bilder **mit Bildunterschrift** — „Blütenstand", „Fiederspaltiges Laubblatt", „Fruchtstand", „Herbarbeleg", „Illustration von …" | Acker-Witwenblume: 10 Bilder, Unterschriften vorhanden | Lizenz nachschlagen wie Commons (dieselben Dateien) |
| **GBIF-Belegfotos** | `occurrence/search?taxonKey=<key>&mediaType=StillImage&country=DE&license=CC0_1_0&license=CC_BY_4_0` → `media[].identifier`, `.license`, `.creator`, `.rightsHolder`, `.publisher`, dazu `eventDate`, `decimalLatitude/Longitude`, `datasetKey` | Knautia DE: **5 555** mit Bild, davon **1 660 CC-BY, 275 CC0** (3 620 CC-BY-NC); Datensätze: Pl@ntNet (CC-BY), NABU-naturgucker (CC-BY), iNaturalist (meist NC, teils CC-BY), Observation.org (NC) | im `media`-Objekt je Bild; **GBIF kennt nur CC0, CC-BY, CC-BY-NC** — `CC_BY_SA_4_0` als Filter gibt HTTP 400 |

**Warum GBIF-Belegfotos zuerst:** sie zeigen **Wildpflanzen an ihrem Standort in
Deutschland**, mit Datum und Ort — der Phänotyp, den der Katalog meint, nicht
die Gartensorte, die Commons-Kategorien mit einsammeln. Das Datum ist obendrein
eine Plausibilitätsprüfung (Aufnahmemonat im GIFT-Blühfenster?) und nebenbei
eine Phänologie-Validierung.

**Quoten je Art (Ziel 12 Bilder):** 6 GBIF-DE (CC0/CC-BY, `HUMAN_OBSERVATION`,
verschiedene Datensätze und Jahre bevorzugt), 4 Commons-„depicts" (dann
Kategorie), 2 Wikipedia-Artikelbilder mit Unterschrift, die „Blüte" oder
„Blütenstand" enthält. Fehlt eine Quelle, füllen die anderen auf; unter **3**
brauchbaren Bildern wird die Art nicht entschieden, sondern gemeldet.

**NC ist standardmäßig ausgeschlossen.** CC-BY-NC ist keine offene Lizenz im Sinn
der Projektregel. Eine Tatsache (die Farbe) ist zwar nicht schutzfähig, und die
Text-und-Data-Mining-Ausnahme (§ 44b UrhG) deckt die Analyse rechtmäßig
zugänglicher Werke — aber der Katalog soll auf Quellen stehen, die er nennen
darf. Ein Schalter `--allow-nc-for-derivation` existiert für die Arten, die sonst
unter drei Bilder fallen, ist standardmäßig aus, und NC-Bilder werden **nie** als
Beleg angezeigt.

**Etikette:** eigener User-Agent mit Kontakt, ≤ 5 Anfragen/s, `maxlag=5` bei
Wikimedia, alles über `ingest/http.py` (Cache, Delay, Retry); Bilder als
640-px-Derivate (Commons per `iiurlwidth`, iNaturalist/Pl@ntNet-URLs in ihrer
`medium`-Variante, sonst Original laden und lokal skalieren), EXIF entfernt,
Originale verworfen. Zwölf Bilder × 4 300 Arten × ~120 KB ≈ **6 GB** in
`data/raw/images/<taxon_id>/` — gitignored, nie im Image.

---

## 3. Grundwahrheit und zweite Meinungen

| Quelle | Rolle | Stand |
|---|---|---|
| **GIFT** (590 Arten, 524 im Kern) | Hold-out-Grundwahrheit für die Primärfarbe; Kalibrierung der Farbgrenzen | vorhanden |
| **BiolFlor** (UFZ; 3 659 Arten der deutschen Flora, Blütenfarbe als Merkmal) | mögliche **zweite Grundwahrheit** — und, falls offen lizenziert, der billigste Weg zur Deckung überhaupt: dann validiert die Bildpipeline BiolFlor und ergänzt Sekundärfarbe, Variabilität und Belegfotos | über TRY erreichbar; TRYs öffentliche Datensätze stehen unter CC BY 3.0, Download nur mit Registrierung; ob BiolFlor darunter fällt, ist **in Feature 0 zu klären** (Datenblatt lesen, Lizenz zitieren) |
| FloraVeg.EU | — | bietet **keinen** Download der Blütenfarbe; nur als Stichprobe zum Nachschlagen |
| Wikipedia-Text (Plan 02, Teil B) | vierte Stimme: „Kronblätter sind gelb" | Regex/LLM aus Plan 02 |

Ehrlich gesagt: sollte BiolFlor unter CC BY nutzbar sein, ist der Datensatz
zuerst zu ingestieren (ein gewöhnlicher `Source`-Adapter) und diese Pipeline
wird zu dem, was sie ohnehin sein sollte — Prüfung, Sekundärfarbe und Belege.
Der Plan gilt in beiden Fällen; nur die Reihenfolge der Features ändert sich.

---

## 4. Architektur: zehn Stufen, jede für sich wiederholbar

Ein CLI `ninanatur-ingest vision <stufe> [--taxa …] [--resume]`, jede Stufe
liest und schreibt **JSONL-Manifeste** unter `data/vision/<stufe>/`, ist
idempotent (Hash-geprüft), fortsetzbar, und pinnt Modellversionen in jedem
Datensatz. Kein Modell läuft im Serving-Pfad; die Abhängigkeiten liegen in
einem Extra `ninanatur[vision]` und in einer **eigenen venv**, weil torch nicht
ins App-Image gehört.

```
S0 survey     Zählen je Art und Quelle, QID-Brücke, Bericht          → survey.jsonl
S1 collect    Kandidaten sammeln, Lizenz filtern, Derivate laden      → images.jsonl + data/raw/images/
S2 triage     Blütenfoto? (CLIP), Unterschrift, Monat, Duplikate      → triage.jsonl
S3 locate     Blüte finden + maskieren (GDINO+SAM2 | Florence-2)      → masks/<id>.png + locate.jsonl
S4 measure    Farben der Maske in CIELAB → Vokabular                  → measure.jsonl
S5 judge      lokales VLM, JSON-Schema                                → judge.jsonl
S6 embed      DINOv2-Embedding des Blütenausschnitts + Probe          → embed.jsonl
S7 aggregate  Stimmen je Art → primär/sekundär/variabel + Konfidenz   → verdicts.jsonl
S8 evaluate   gegen GIFT (+ BiolFlor), Konfusion, Fehlerklassen       → report.html
S9 review     Kontaktbogen je strittiger Art, Tastatur-Entscheid      → reviews.jsonl
S10 write     upsert_trait + Belegtabellen; export-catalogue          → DB
```

Datenfluss-Regel: eine Stufe darf nur ihre Vorgänger lesen; S10 ist der einzige
Schreiber in die Datenbank, und er schreibt nur über `upsert_trait`.

### S0 — survey

Für jede Art der Zielmenge: QID (SPARQL in 200er-Blöcken; Rückfall
`wbsearchentities` mit dem kanonischen Namen), Anzahl Commons-„depicts",
Anzahl Kategorie-Dateien, Anzahl Wikipedia-Bilder (de/en), Anzahl GBIF-Bilder
je Lizenz (DE und weltweit). Ausgabe: eine Tabelle und die Liste der Arten
unter der Schwelle. Kosten: ~4 Anfragen je Art, 4 300 Arten, 0,3 s Abstand →
**~1,5 h**, vollständig gecached.

### S1 — collect

Kandidatenliste je Art nach Quoten (Abschnitt 2), Lizenz **je Bild** geprüft
(Commons `extmetadata`, GBIF `media.license`), unbekannte oder NC-Lizenz →
verworfen (protokolliert). Download des 640-px-Derivats, SHA-256 und
Wahrnehmungs-Hash (pHash) gegen Dubletten (dasselbe Foto liegt oft auf Commons
und bei Pl@ntNet), EXIF-Strip. Jede Zeile in `images.jsonl`: `image_id`,
`taxon_id`, Quelle, URL, Seite, Autor, Lizenz, `AttributionRequired`,
Aufnahmedatum/-ort (GBIF), Bildunterschrift (Wikipedia), Maße, Hashes.

### S2 — triage

Zero-Shot-Klassifikation mit CLIP (ViT-B/32, MIT) oder SigLIP (Apache) gegen
Prompts: *„a photo of a flower", „a close-up of flowers", „a plant with leaves
and no flowers", „a herbarium specimen", „a botanical illustration",
„a distribution map", „seeds or fruits", „a landscape/habitat", „bark or
trunk", „an insect on a flower"*. Behalten: Blüte/Nahaufnahme (auch mit Insekt).
Zusätzlich: Wikipedia-Unterschrift mit „Herbar", „Illustration", „Laubblatt",
„Frucht", „Samen" → raus; GBIF-Aufnahmemonat außerhalb `flowering_start/end`
(±1 Monat, mit Jahreswechsel-Logik aus `bloom/timeline.py`) → herabgestuft,
nicht verworfen. Ausgabe: `keep`, `reason`, CLIP-Scores. ~30 Bilder/s auf dem M1.

### S3 — locate

**Vorzugsweg:** Grounding DINO *tiny* (Apache-2.0, `IDEA-Research/grounding-dino-tiny`)
mit dem Prompt `"flower . blossom . inflorescence . flower head ."`,
Box-Schwelle 0,30, Text-Schwelle 0,25, höchstens 12 Boxen; dann SAM 2
*hiera-small* (Apache-2.0) mit den Boxen als Prompt → Masken. **Ein-Modell-Weg
für den M1:** Florence-2 *large* (MIT, 0,77 B) mit
`<CAPTION_TO_PHRASE_GROUNDING>` „flower" und
`<REFERRING_EXPRESSION_SEGMENTATION>` — weniger Speicher, ein Durchlauf.
Qualitätstore je Maske: Fläche 1–60 % des Bildes, Score ≥ 0,35, Erosion um
2 px (Blattkanten), Vereinigung überlappender Masken. Behalten werden bis zu 5
Masken je Bild, sortiert nach Fläche × Score. Ausgabe: PNG-Masken und Statistik.

### S4 — measure (Abschnitt 6 im Detail)

### S5 — judge (Abschnitt 7 im Detail)

### S6 — embed

DINOv2-small (Apache-2.0) oder SigLIP-Embedding des um 10 % erweiterten
Blütenausschnitts; eine logistische Regression auf den GIFT-Arten (Trainingsbilder
der 524 Kernarten, stratifiziert, 5-fach kreuzvalidiert) sagt die Primärfarbe
mit Wahrscheinlichkeit vorher. Zusätzlich ein Out-of-Distribution-Score
(Abstand zum nächsten Trainings-Cluster) als Warnung „so ein Bild kenne ich
nicht". Dritte Stimme, bewusst schwach gewichtet (0,5).

### S7 — aggregate (Abschnitt 8)

### S8 — evaluate (Abschnitt 9)

### S9 — review

Ein statischer HTML-Kontaktbogen je strittiger Art: die Bilder mit Maske
eingefärbt, die drei Stimmen je Bild, die Aggregation, GIFT/BiolFlor daneben,
Tastatur: `1–0` Farbe setzen, `s` Sekundärfarbe, `v` variabel, `x` unbrauchbar,
`n` weiter. Entscheidungen in `reviews.jsonl` mit Reviewer und Zeit. Ein
Mensch schafft ~150 Arten je Stunde; bei 20 % strittigen Arten sind das zwei
bis drei Stunden für die erste Stufe.

### S10 — write

`upsert_trait(taxon_id, "flower_colour", source="ninanatur-cv-1", license=…,
value_text=…, confidence=…)`, ebenso `flower_colour_secondary` und
`flower_colour_variability` (`fixed` | `variable`); Belegtabellen (Abschnitt 10);
`KNOWN_TRAIT_KEYS` erweitert; `export-catalogue`; Startup-Sync bringt es auf
jedes Volume. **Eine menschliche Bestätigung** setzt `confidence = 1.0` und
`reviewed_by`; ein menschlicher Widerspruch schreibt den Menschen, nicht die
Maschine — und beides bleibt im Beleg nachlesbar.

---

## 5. Modelle und Laufzeit — auf dieser Maschine

Gemessen: Apple **M1, 8 Kerne, 16 GB**, kein torch, kein mlx, kein ollama.
Alles unten läuft darauf, aber nacheinander, nie zwei große Modelle zugleich.

| Aufgabe | Modell | Größe | Lizenz | M1 16 GB (Schätzung, in Feature 1 messen) | GPU (RTX 4090, gemietet) |
|---|---|---|---|---|---|
| Triage | CLIP ViT-B/32 · SigLIP-B | 150–400 M | MIT · Apache-2.0 | ~30 Bilder/s | 500/s |
| Finden | Grounding DINO tiny | 172 M | Apache-2.0 | 0,7–1,5 s/Bild (MPS) | 25/s |
| Maskieren | SAM 2 hiera-small | 46 M | Apache-2.0 | 0,3–0,6 s/Bild | 40/s |
| Finden + Maskieren | Florence-2 large | 770 M | MIT | 1–2 s/Bild | 15/s |
| Urteilen | **Qwen3-VL-8B** (Q4) über Ollama (nutzt MLX auf Apple Silicon) oder MLX-VLM; **Qwen3-VL-4B** wenn der Speicher drückt | 4–8 B | Apache-2.0 | 3–8 s/Bild bei 640 px | 10–20 Bilder/s gebatcht (vLLM) |
| Embedding | DINOv2-small | 22 M | Apache-2.0 | ~30 ms | — |
| Farbmetrik | numpy + scikit-image (Lab, k-means) | — | BSD | ~20 ms | — |

Alternativen mit Vorbehalt: InternVL3 (MIT, stark, größer), Pixtral 12B
(Apache-2.0, passt nicht in 16 GB), Gemma 3/4 (Gemma-Lizenz — Nutzungsbedingungen
lesen), Molmo2 (Apache-2.0, stark im Zeigen — für die Frage „wo ist die Blüte"
interessant). Modellwahl und Lizenzen werden in Feature 0 gegen die aktuellen
Modellkarten geprüft; die Tabelle ist der Stand vom 2026-09-07.

**Budget für 35 000 Bilder (4 300 Arten × ~8 brauchbare):**

| Stufe | M1 | gemietete GPU |
|---|---|---|
| S1 Download | 6 GB, ~2 h (höflich) | dieselben 2 h |
| S2 Triage | 20 min | 1 min |
| S3 Locate | 8–20 h → **zwei Nächte** | 30 min |
| S5 Judge (nur die 4 besten Bilder je Art ≈ 17 000) | 15–35 h → **drei Nächte** | 30–60 min |
| S6 Embed | 20 min | 1 min |
| S4/S7/S8 | Minuten | Minuten |

Beides ist realistisch. Die GPU-Variante kostet einige Euro Mietzeit und verschickt
nur öffentliche Bilder — keine Nutzerdaten. Der M1 kostet Nächte.

---

## 6. Die Farbmetrik im Detail

1. **Farbraum.** sRGB → linear → XYZ (D65) → **CIELAB**; Farbabstände als
   ΔE2000. Alles in `numpy`/`scikit-image`, keine weitere Abhängigkeit.
2. **Pixelauswahl.** Maskenpixel nach Erosion (2 px); ausgeschlossen: Glanzlichter
   (L\* > 97), Tiefschatten (L\* < 8). Gewichtung nach Abstand zum Maskenrand
   (Randpixel 0,5), damit Blattkanten und Halbschatten wenig zählen.
3. **Clustern.** k-means (k = 4, k-means++, fester Seed) im Lab; Cluster mit
   ΔE2000 < 12 zueinander werden vereinigt; Cluster unter 6 % Fläche fallen weg.
4. **Benennen.** Jedes Clusterzentrum wird über **Regeln in Lab/LCh** einer der
   zehn Farben zugeordnet — Startwerte, die in Feature 3 an den GIFT-Arten
   **kalibriert** werden (Rastersuche über die Grenzen, Ziel: makro-F1, 5-fach):

   | Farbe | Startregel (L\*, C\*, h in Grad) |
   |---|---|
   | white | L > 85 und C < 12 (oder L > 90 und C < 16) |
   | black | L < 22 |
   | brown | h 20–70, C 10–45, L < 62 |
   | yellow | h 80–105, C > 25 |
   | orange | h 45–80, C > 30, L > 55 |
   | red | h 350–25 (über 0), C > 35, L < 62 |
   | pink | h 330–15 mit L > 58 oder C < 40 — die helle, blasse Rot-Familie |
   | violet | h 285–330, C > 15 |
   | blue | h 230–285, C > 15 |
   | green | h 100–180, C > 15 |

   Grenzfälle sind absichtlich sichtbar: rosa/violett bei h 320–335, gelb/orange
   bei h 75–85. Für sie wird der **zweitnächste Name** mitgeführt; die
   Aggregation (Abschnitt 8) darf ihn verwenden.
5. **Je Bild:** Liste `(farbe, anteil)` sortiert; **primär** = größter Anteil,
   wenn ≥ 0,45; **sekundär** = nächste *andere* Farbe mit Anteil ≥ 0,18 und
   ΔE2000 ≥ 20 zum Primärzentrum; sonst keine. Ein Bild, dessen Primärfarbe
   „green" ist, während das VLM „keine grüne Blüte" sagt, wird als
   Maskenfehler (Blatt) markiert — Wolfsmilch und Frauenmantel bleiben grün,
   weil dort beide Stimmen übereinstimmen.
6. **Weißabgleich.** Kein globaler Eingriff: Grey-World färbt Blütenfotos, die
   ohnehin von einer Farbe dominiert werden, falsch um. Ein Farbstich wird
   stattdessen vom VLM erfragt („strong colour cast?") und senkt das
   Bildgewicht; das Mehrbild-Mittel trägt den Rest.
7. **Zentrum vs. Kranz.** Die Sekundärfarbe der Margerite (gelbes Körbchen) ist
   wahr; der Pixelweg findet sie als zweites Cluster, das VLM benennt sie als
   „centre". Beide müssen sie nennen, sonst wird sie nicht gespeichert.

---

## 7. Das VLM-Urteil: Prompt und Schema

Ein Aufruf je Bild, 640 px, `temperature 0`, Antwort **erzwungen als JSON**
(Ollama `format` mit JSON-Schema; MLX-VLM mit Nachparsen und Wiederholung),
Prompt auf Englisch (die Modelle sind darauf am zuverlässigsten), das
Vokabular als geschlossene Aufzählung:

```
You are labelling photographs for a botanical database. The photo is said to show
the plant species "{scientific_name}" ({german_name}).
Answer ONLY with JSON matching the schema. Use exactly these colour words:
yellow, white, pink, violet, blue, red, orange, green, brown, black.
- flower_visible: are open flowers clearly visible? (true/false)
- flower_part: what is coloured — "petals", "bracts", "flower_head", "catkin",
  "none"
- colours: the colours of the showy flower parts, most prominent first, with
  an estimated share (0–1) each; list a second colour only if it is clearly a
  different colour word (e.g. a yellow centre on white petals).
- centre_colour: colour of the flower centre if clearly different, else null
- colour_cast: does the photo have a strong colour cast or bad exposure? (true/false)
- likely_cultivar: does this look like a garden cultivar rather than the wild
  type (unusual colour, double flowers, garden setting)? (true/false)
- other_species: is another flowering species prominent in the frame? (true/false)
- confidence: your confidence in the colour answer (0–1)
```

Schema-Felder genau so, `additionalProperties: false`. Parse-Fehler werden
gezählt und einmal wiederholt; ein zweiter Fehler macht das Bild für S5
unbrauchbar (nicht für S4). Das Modell und die Prompt-Version stehen in jeder
Zeile von `judge.jsonl`. Kein Few-Shot — Beispielbilder würden die Antwort
an ihre Farben binden.

---

## 8. Aggregation und Konfidenz

Je Bild drei Stimmen: **Pixel** (S4), **VLM** (S5), **Probe** (S6). Gewichte:

    w_pixel = 1,0 × Maskenqualität (0,5–1,0)
    w_vlm   = 1,0 × confidence × (0,6 wenn colour_cast) × (0,5 wenn likely_cultivar)
    w_probe = 0,5 × Wahrscheinlichkeit

Ein Bild fällt ganz heraus, wenn `flower_visible = false` oder `other_species
= true` oder die Triage es herabgestuft hat und die Stimmen uneins sind.

Je Art: Summe der Gewichte je Farbe über alle Bilder → **primär** = Maximum;
`share_primary` = sein Anteil an der Gesamtsumme.

    confidence = share_primary
               × min(1, n_bilder / 6)
               × (1,0 bei ≥ 2 Quellen, 0,85 bei einer Quelle)

| Ergebnis | Regel |
|---|---|
| **schreiben** | confidence ≥ 0,75 und n_bilder ≥ 3 |
| **schreiben + Review** | 0,50 ≤ confidence < 0,75 |
| **nur Review** | confidence < 0,50 oder n_bilder < 3 |
| **variabel** | eine zweite Farbe trägt ≥ 35 % der Bild-Primärstimmen und liegt ΔE2000 ≥ 20 entfernt → beide gespeichert, `variability = variable` |
| **Sekundärfarbe** | dieselbe Sekundärfarbe in ≥ 50 % der Bilder, von Pixel **und** VLM genannt |
| **Grenzfall** | rosa/violett bzw. gelb/orange: wenn die Zweitnamen der Pixelstimme das Bild kippen, entscheidet das VLM; bleibt es uneins → Review |

Beispiel Margerite: 8 Bilder, Pixel: weiß 0,62 / gelb 0,25; VLM: weiß, Zentrum
gelb in 7 von 8; Probe: weiß 0,9 → primär weiß, sekundär gelb, confidence
≈ 0,9 → schreiben.

---

## 9. Validierung — das Tor vor dem Ausrollen

- **Hold-out:** die 524 GIFT-Kernarten, stratifiziert nach Farbe; die
  Farbgrenzen (S4) und der Probe (S6) werden nur auf 4 der 5 Falten
  kalibriert/trainiert, die fünfte misst.
- **Metriken:** Trefferquote der Primärfarbe, makro-F1, Top-2-Treffer,
  Konfusionsmatrix — rosa↔violett, gelb↔orange, weiß↔rosa sind die erwarteten
  Verwechslungen und werden einzeln ausgewiesen; Einigkeit der drei Stimmen als
  eigene Kennzahl (wo sie uneins sind, ist das Review-Budget).
- **Schwellen vor dem Ausrollen:** ≥ 85 % Primärtreffer, ≥ 92 % Top-2, keine
  Farbklasse unter 70 % Recall (schwarz/braun ausgenommen, zu selten). Darunter
  wird kalibriert, nicht ausgerollt.
- **Fehlerklassen** im Bericht: Maske daneben (Blatt), Sorte statt Wildform,
  Farbstich, Zentrum als Primärfarbe, GIFT selbst fraglich (das gibt es: GIFT
  ist eine Aggregation und trägt eigene Fehler — eine Stichprobe von 30
  Widersprüchen wird von Hand angesehen, bevor die Pipeline die Schuld bekommt).
- **BiolFlor** als zweite Prüfmenge, falls nutzbar; die Übereinstimmung
  GIFT↔BiolFlor selbst ist die Messlatte dafür, was „richtig" überhaupt
  bedeutet — zwei Datensätze werden sich bei rosa/violett auch nicht einig sein.

---

## 10. Provenienz-Schema

Ingest-Zeit (bleibt in der lokalen DB, **nicht** im ausgelieferten Katalog —
wie `interaction`):

```sql
CREATE TABLE IF NOT EXISTS image_asset (
    image_id      TEXT PRIMARY KEY,      -- sha256 des Derivats
    taxon_id      INTEGER NOT NULL REFERENCES taxon(taxon_id),
    source        TEXT NOT NULL,         -- 'commons:depicts' | 'commons:category' | 'wikipedia:de' | 'gbif:<datasetKey>'
    url           TEXT NOT NULL,         -- Derivat-URL, die angezeigt werden darf
    page_url      TEXT NOT NULL,         -- Dateiseite / Beleg
    author        TEXT, licence TEXT NOT NULL, attribution_required INTEGER NOT NULL,
    taken_on      TEXT, lat REAL, lon REAL, caption TEXT,
    width INTEGER, height INTEGER, phash TEXT,
    fetched_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS colour_observation (
    image_id      TEXT NOT NULL REFERENCES image_asset(image_id),
    method        TEXT NOT NULL,         -- 'pixel' | 'vlm' | 'probe'
    model         TEXT NOT NULL,         -- z. B. 'qwen3-vl:8b-q4@2026-09' / 'gdino-tiny+sam2-small'
    primary_colour TEXT, secondary_colour TEXT, shares TEXT,   -- JSON
    quality       REAL, flags TEXT,      -- JSON: cast, cultivar, other_species, mask_area
    observed_at   TEXT NOT NULL,
    PRIMARY KEY (image_id, method, model)
);
```

Katalog (**wird ausgeliefert**, klein):

```sql
CREATE TABLE IF NOT EXISTS colour_verdict (
    taxon_id      INTEGER PRIMARY KEY REFERENCES taxon(taxon_id),
    primary_colour TEXT NOT NULL, secondary_colour TEXT,
    variability   TEXT NOT NULL,         -- 'fixed' | 'variable'
    alternatives  TEXT,                  -- JSON: [{colour, share}]
    confidence    REAL NOT NULL, n_images INTEGER NOT NULL, n_sources INTEGER NOT NULL,
    pipeline      TEXT NOT NULL,         -- 'ninanatur-cv-1'
    reviewed_by   TEXT, reviewed_at TEXT,
    decided_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS colour_evidence (        -- bis zu 3 Belegfotos je Art
    taxon_id INTEGER NOT NULL REFERENCES taxon(taxon_id),
    url TEXT NOT NULL, page_url TEXT NOT NULL, author TEXT, licence TEXT NOT NULL,
    PRIMARY KEY (taxon_id, url)
);
```

Die `trait`-Zeilen selbst: `flower_colour` (primär), `flower_colour_secondary`,
`flower_colour_variability`, alle mit `source='ninanatur-cv-1'`,
`license='derived from CC0/CC-BY/CC-BY-SA images; see colour_evidence'`,
`confidence` aus Abschnitt 8. `CATALOGUE_TABLES` bekommt `colour_verdict` und
`colour_evidence` (≈ 4 300 × 3 × 200 B ≈ 2,6 MB — im Budget des 10-MB-Katalogs,
zu messen). `SOURCE_PRIORITY` wird `("EIVE-1.0", "GIFT", "ninanatur-cv-1")`;
`manual` bleibt dahinter (Doc 62: eine Handeingabe füllt eine Lücke, bis eine
Quelle sie füllt). Ob ein Gärtner vor Ort die Maschine schlagen soll, ist eine
Entscheidung (Abschnitt 16); die Alternativen bleiben in jedem Fall sichtbar.

---

## 11. Anschluss an die Seite

- Info-Panel: *„Blütenfarbe: rosa — aus 8 Fotos ermittelt, Konfidenz 0,82.
  Sekundär: gelb (Zentrum)."* Darunter drei Belegfotos als Thumbnails
  (**verlinkt, nicht kopiert** — wie `species_info` Wikipedia verlinkt), jedes
  mit Autor, Lizenz und Link zur Dateiseite. Attribution ist Bedingung, keine
  Fußnote.
- Die Farbpunkte (`ClusterLayer`) malen die Primärfarbe; bei `variable` beide
  Farben im Verhältnis der Anteile; die Sekundärfarbe als kleiner Kern des
  Punktes, wo sie existiert — genau die Margerite.
- `ColourNote` bleibt; zeigt aber, was die Maschine sagt, bevor der Gärtner
  widerspricht, und ein Widerspruch landet als `manual` daneben.
- Die CSP (Plan 01) muss `upload.wikimedia.org`, `inaturalist-open-data.s3.amazonaws.com`,
  Pl@ntNet- und naturgucker-Hosts als `img-src` erlauben — genau die Hosts der
  Belege, keine anderen.

---

## 12. Tests — offline, ohne Modelle

- **Farbmetrik:** synthetische Bilder (farbige Scheibe auf grünem Grund, mit
  Glanzlicht und Schatten) → erwartete Primär-/Sekundärfarbe; Grenzfarben
  (h = 330, 80) liefern beide Namen.
- **Goldene Menge:** 30 echte Bilder (offen lizenziert, im Repo als Fixture,
  klein) mit aufgezeichneten Modellausgaben (Masken, VLM-JSON, Embeddings) als
  Dateien — die Tests prüfen S4, S7 und S10 auf diesen Aufzeichnungen; kein
  Test lädt ein Modell oder das Netz (`conftest.py`-Regel).
- **Aggregation:** Regeln aus Abschnitt 8 als Tabelle-getriebene Tests
  (Margerite, Buschwindröschen, eine Art mit 2 Bildern → Review).
- **Provenienz:** ein Wert ohne Belegfoto kann nicht geschrieben werden; jeder
  Beleg trägt Lizenz und Autor, wenn `attribution_required`; NC wird ohne
  Schalter abgewiesen; `flower_colour_secondary` steht in `KNOWN_TRAIT_KEYS`.
- **Vokabular:** der Pipeline-Farbsatz == `DRAWABLE` == `colours.ts`
  (`test_kind_vocabulary.py`-Muster).
- **Katalog:** `export-catalogue` mit `colour_verdict`/`colour_evidence`
  bleibt unter der Größenschwelle; `sync_catalogue` reicht sie auf ein leeres
  Volume durch (die eine Prüfung gegen ein frisches Volume, die `CLAUDE.md`
  verlangt).

---

## 13. Budgets, zusammengefasst

| | Wert |
|---|---|
| Anfragen S0 | ~17 000, ~1,5 h, gecached |
| Bilder | ≤ 12 je Art, ~35 000 gesamt, ~6 GB Derivate in `data/raw/images/` (gitignored) |
| Rechenzeit M1 | 3–5 Nächte (S3 zwei, S5 drei) — oder 1–2 h auf gemieteter GPU |
| Speicher DB (Ingest) | `image_asset` + `colour_observation` ≈ 100 000 Zeilen, ~40 MB |
| Speicher Katalog | ≈ 2,6 MB zusätzlich |
| Menschliche Prüfung | ~20 % der Arten strittig → 250 Arten je Stufe → 2–3 h |

---

## 14. Rechtliches, kurz und ehrlich

- Ein Farbwert ist eine Tatsache; die Analyse rechtmäßig zugänglicher Bilder
  ist Text-und-Data-Mining. Der Katalog stützt sich trotzdem nur auf Bilder,
  die er nennen darf (CC0, CC-BY, CC-BY-SA, gemeinfrei), weil er sie **zeigt**.
- CC-BY-SA-Thumbnails **verlinkt** anzuzeigen ist keine Bearbeitung; Attribution
  und Link sind Pflicht und stehen am Bild.
- Keine Quelle ohne API-Nutzungsbedingungen und `robots.txt`; nie NaturaDB
  oder vergleichbare kuratierte Datenbanken (`CLAUDE.md`).
- Modell-Lizenzen (Apache-2.0, MIT) erlauben die Nutzung; Gemma-Modelle nur
  nach Lesen der Nutzungsbedingungen. Alle Modellkarten werden in Feature 0
  zitiert.
- Kein Nutzerbild verlässt die Maschine; die Pipeline verarbeitet nur
  öffentliche Bilder.

---

## 15. Risiken und Grenzen

| Risiko | Antwort |
|---|---|
| **Sorten statt Wildform** auf Commons | GBIF-Belegfotos zuerst; VLM-Flag `likely_cultivar`; Commons-Dateinamen mit `'…'`, „cv.", „cultivar" ausgeschlossen |
| **rosa ↔ violett**, gelb ↔ orange | kalibrierte Grenzen, Zweitnamen, VLM entscheidet, Review als Rückhalt; im Bericht ausgewiesen, nicht versteckt |
| **Farbstich, Blitz, Abendlicht** | VLM-Flag, Bildgewicht, Mehrbild-Mittel |
| **grün blühende Arten** | zwei Stimmen müssen grün sagen; sonst gilt es als Blatt |
| **Winzige Blüten** (Labkraut, Vergissmeinnicht-Verwandte) | Masken unter 1 % verworfen → Bild fällt; die Art landet im Review mit Nahaufnahmen-Hinweis |
| **Falsch bestimmte Belegfotos** | nur `HUMAN_OBSERVATION` aus Pl@ntNet/naturgucker/iNat-CC-BY; Mehrbild-Mittel; Ausreißer (VLM `other_species`) raus |
| **Frucht- und Knospenbilder** | Triage + Aufnahmemonat |
| **M1-Speicher** | Modelle nacheinander, 640 px, Q4; notfalls Qwen3-VL-4B; oder GPU mieten |
| **Modell-/API-Drift** | Versionen in jeder Zeile; Manifeste hash-geprüft; ein Rerun kostet null Downloads |

---

## 16. Entscheidungen für den Owner

1. **BiolFlor zuerst prüfen** (Lizenz über TRY). Ja oder nein entscheidet, ob
   die Pipeline die Deckung *bringt* oder *prüft*.
2. **NC-Bilder** nur mit Schalter und nie als Beleg (empfohlen) — oder ganz aus.
3. **Rang gegen `manual`:** Maschine vor Gärtner (empfohlen, mit sichtbaren
   Alternativen) oder Gärtner vor Maschine.
4. **Vokabular** bei zehn Farben lassen (empfohlen — die Zeichenschicht kennt nur
   sie) oder um `purple`/`cream` erweitern, was Zeichenschicht, Filter und
   Frontend mitziehen müsste.
5. **Rechnen auf dem M1** (Nächte) oder auf gemieteter GPU (Stunden, einige Euro).

---

## 17. Reihenfolge und Aufwand

| # | Feature | Inhalt | PT |
|---|---|---|---|
| 0 | which-pictures-and-whose | S0 auf der Zielmenge; Lizenztexte je Quelle; BiolFlor/TRY geklärt; Modellkarten zitiert; Bericht mit Deckung | 1,5 |
| 1 | twelve-pictures-of-each | S1 + S2 mit Lizenzfilter, Dubletten, Derivaten; Budget-Tests | 2 |
| 2 | where-the-flower-is | S3 (GDINO+SAM2 oder Florence-2), Qualitätstore, Masken-Kontaktbogen für 50 Arten | 2 |
| 3 | what-colour-it-is | S4 mit kalibrierten Grenzen an GIFT (Hold-out), Goldene Menge | 2 |
| 4 | a-second-opinion | S5 (VLM, Schema) + S6 (Probe) | 2 |
| 5 | one-answer-per-species | S7 + S8, Bericht mit Konfusion und Fehlerklassen; Schwellen | 1,5 |
| 6 | somebody-looked | S9 Kontaktbogen, Reviews | 1,5 |
| 7 | written-with-its-pictures | S10, Schema, `export-catalogue`, Info-Panel mit Belegen, Farbpunkte mit Sekundärfarbe, CSP-Hosts | 2,5 |

Etwa **15 Personentage** plus die Rechennächte. Feature 0–3 sind der messbare
Kern; ab Feature 5 fließen die ersten Werte in den Katalog. Als **Wave 28**
(`.mdd/waves/ninanatur-wave-28.md`) zugeschnitten: hängt an Wave 24, weil die
Farbtupfer mit Sekundärfarbe auf dem gezeichneten Plan landen; die Stufen 1–2 sind
Ingest-Arbeit und können jederzeit als Hintergrundjob laufen. Doc → Test → Code,
jede Stufe mit ihrem Manifest als Definition of done.
