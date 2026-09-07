# Plan — Blütenfarben aus Bildern, Merkmale aus Texten

> Zwei Anreicherungs-Pipelines für den Katalog, beide gegen die eine Frage
> gebaut, die dieses Projekt formt: *woher kommt der Wert, unter welcher Lizenz,
> wie sicher?* Jeder erzeugte Wert geht durch `provenance.upsert_trait` und trägt
> `source`, `license`, `confidence`, `retrieved_at` — sonst wirft der eine
> Schreibpfad. Beide sind **Ingest-Zeit**, laufen offline, cachen über
> `ingest/http.py`, und landen im ausgelieferten Katalog. Kein Modell auf dem
> Serving-Pfad.
>
> Zahlen unten sind am 2026-09-07 gegen `ninanatur/data/catalogue.sqlite`
> (8 939 Arten) und mit Stichproben gegen die deutsche Wikipedia / Commons /
> Wikidata gemessen, nicht geschätzt — dieselbe Disziplin wie „Deckung messen,
> bevor geplant wird".

---

## Ausgangslage: was der Katalog heute wirklich hält

Gemessen, nicht gehofft. `trait`-Schlüssel mit Quelle und Deckung über die
8 939 deutschen Arten, und über den engeren „Kernsatz" (die ~4 300 mit allen vier
Ellenberg-Achsen, aus dem die Vorschläge kommen):

| Merkmal (Frage des Nutzers) | trait_key | Quelle | Deckung /8 939 | im Kernsatz |
|---|---|---|---|---|
| Blütenfarbe (primär) | `flower_colour` | GIFT | **590 (6,6 %)** | 524 |
| Blütenfarbe (sekundär) | — | — | **0** | 0 |
| Wuchshöhe | `height_max_m` | GIFT | 3 952 (44 %) | 3 293 |
| Bodennährwert | `ellenberg_n` | EIVE | 4 326 (48 %) | — |
| Feuchte | `ellenberg_m` | EIVE | 4 425 | — |
| Boden-pH/Reaktion | `ellenberg_r` | EIVE | 4 351 | — |
| Sonne/Schatten (Licht) | `ellenberg_l` | EIVE | 4 384 (49 %) | — |
| Blütezeit | `flowering_start/end_month` | GIFT | 3 671 / 3 560 (41 %) | 3 176 |
| Wuchsform | `growth_form` | GIFT | 4 345 | 3 346 |
| Lebensform | `life_form` | GIFT | 3 862 | — |
| Lebenszyklus | `lifecycle` | GIFT | 4 489 | 3 467 |
| Verholzung | `woodiness` | GIFT | 4 640 | 3 528 |
| Bestäubung | `pollination_syndrome` | GIFT | 2 375 | 2 148 |
| Laubabwurf | `deciduousness` | GIFT | 452 (Gehölze) | — |
| Heimisch in DE | `native_de` | GBIF-WCVP | 8 939 (100 %) | — |
| **Aussaat / „wann säen"** | — | — | **0** | 0 |

**Was daraus folgt für die zwei Aufgaben:**

- **Farbe ist das größte Loch:** 6,6 % Deckung, nur *ein* kategorialer Wert aus
  zehn (`yellow, white, pink, violet, blue, red, green, orange, brown, black`),
  keine Sekundärfarbe. Und es ist genau da am dünnsten, wo das Produkt es am
  meisten braucht: **1 218 Arten im Kernsatz sind als insektenbestäubt geführt
  und haben keine Farbe** — der Blütenkalender und die Farbpunkte auf der Karte
  laufen für die auf „unbekannt".
- **Sonne/Schatten, Nährwert, Feuchte, pH** sind als **Ellenberg-Konvention**
  vorhanden (48–49 %), nicht als zitierbarer Klartext — die App zeigt heute eine
  abgeleitete Zahl, keine Aussage aus einer Quelle. Textextraktion kann beides:
  die 51–56 %-Lücke füllen *und* einen zitierbaren Prosa-Beleg neben die Zahl
  stellen.
- **Wuchshöhe und Blütezeit** liegen bei ~41–44 % — die deutsche Wikipedia trägt
  beide sehr regelmäßig im Fließtext (siehe Stichproben unten).
- **Aussaat gibt es nirgends** und Wikipedia trägt es zuverlässig **nicht** (das
  ist gärtnerisch, Wikipedia ist botanisch). Das ist die ehrlich schwächste
  Teilaufgabe — siehe 2.6.

---

# Teil 1 — Blütenfarben-Annotationspipeline (primär + sekundär)

## 1.1 Warum aus Bildern

GIFT gibt 590 Farben. Der Rest der Flora ist auf Fotos gut belegt: die Stichprobe
gegen die deutsche Wikipedia fand **21 von 30 Kernarten mit Artikel, alle 21 mit
Bild** — und Commons hält pro Art oft Dutzende lizenzklare Fotos (Beispiel
*Knautia arvensis*: 50 Dateien in der Art-Kategorie). Die Farbe steht also im
Bild; sie muss nur verlässlich und lizenzkonform herausgelesen werden.

## 1.2 Die Bildquelle — und warum nicht das REST-Thumbnail allein

Es gibt schon einen Wikipedia-Pfad (`data/species_info.py`, REST-Summary,
**auf dem Volume** gecached). Dessen Thumbnail ist aber (a) nur *ein* Bild, (b)
manchmal eine Illustration oder ein Habitus-Foto ohne offene Blüte, und (c) seine
Lizenz-/Urhebermetadaten liegen nicht strukturiert vor.

**Besser: Wikimedia Commons als primäre Bildquelle**, denn dort kommt die Lizenz
strukturiert mit:
- `action=query&list=categorymembers&cmtitle=Category:<wissenschaftlicher Name>&cmtype=file`
  → die Fotos der Art.
- Pro Datei `prop=imageinfo&iiprop=url|size|mime|extmetadata&iiurlwidth=640` →
  Thumbnail-URL **plus** `extmetadata`: `LicenseShortName`, `License`, `Artist`,
  `Credit`, `AttributionRequired`, `UsageTerms`. Stichprobe bestätigt: sauber
  auswertbar (Beispiel lieferte CC0, `AttributionRequired: false`).
- Der Bezug Art→Kategorie kommt aus dem wissenschaftlichen Namen (den der Katalog
  hat) oder robuster über **Wikidata**: `P225` (Taxon-Name) → Item →
  `P373`/Sitelink Commons-Kategorie, `P18` (Bild), `P846` (GBIF-ID, direkter Join
  auf unseren `taxon`). Das ist der verlässliche Schlüssel, weil er nicht von der
  Schreibweise abhängt.

**Lizenzregel (nicht Deko):** nur Bilder mit offener Lizenz (CC0, CC-BY, CC-BY-SA,
PD) verwenden. Für den *abgeleiteten Farbwert* zählt die Lizenz des Bildes nicht
direkt — eine Farbe ist eine Tatsache, kein Werk —, aber die **Attribution des
Bildes muss gespeichert werden**, damit ein Beleg-Ansicht („woher weiß die App
das") den Fotografen nennen kann, so wie `species_info` die Wikipedia-Quelle
nennt. Bilder unklarer Lizenz werden übersprungen, nicht geraten.

## 1.3 Die Erkennung: Grounding DINO + SAM

Der Vorschlag des Nutzers ist richtig; die Reihenfolge ist das Wichtige.

1. **Lokalisieren — Grounding DINO** (open-vocabulary Detektor) mit
   Text-Prompt `"flower . blossom . bloom"` → Bounding-Box(en) der Blüte(n).
   Das trennt die Blüte vom Laub, vom Hintergrund, vom bestäubenden Insekt.
   Ohne diesen Schritt „sieht" ein reiner Farb-Cluster auf dem ganzen Bild
   überwiegend **Grün** (Blatt/Stängel dominieren die Fläche) — das ist der
   Grund, warum naive dominante-Farbe-Ansätze bei Pflanzenfotos scheitern.
2. **Segmentieren — SAM / SAM 2** mit der DINO-Box als Box-Prompt → pixelgenaue
   Maske nur der Blütenblätter. (SAM 2 ist der aktuellere Nachfolger; beide
   liefern Masken aus Box-Prompts.)
3. **Qualität prüfen:** Maskenfläche im plausiblen Bereich (nicht 2 % → wohl keine
   offene Blüte; nicht 95 % → wohl Fehlsegmentierung), DINO-Score über Schwelle.
   Bilder, die durchfallen, werden verworfen — lieber kein Wert als ein falscher.

**Bezugsquelle der Modelle:** lokal ausführbar (Grounding DINO und SAM/SAM 2 sind
offene Gewichte), also **kein externer API-Call auf dem Ingest-Pfad** — passt zur
Projektregel, dass ausgehende Aufrufe durch `ingest/http.py` gehen und ein Rerun
null Requests kostet. Die Modelle sind eine Dev-/CI-Abhängigkeit des
Ingest-Extras, nicht der Laufzeit (das Image bleibt schlank; sie kommen nie in
`requirements` der App).

## 1.4 Von der Maske zur Farbe — primär und sekundär

Über die Blüten-Maske:
1. Pixel in **CIELAB** umrechnen (wahrnehmungsgleichmäßiger Abstand — der Grund,
   warum „violett vs. blau" dort trennt, wo RGB-Abstand lügt).
2. **k-means** (oder Mean-Shift) auf den Maskenpixeln; Cluster nach Flächenanteil
   sortieren. Weiß-/Überbelichtungs-Pixel und sehr dunkle Schatten vorher kappen
   (sonst wird jede Blüte „weiß" oder „schwarz").
3. Jedes Cluster-Zentrum auf das **10-Farben-Vokabular** abbilden: nächster
   Nachbar zu 10 in Lab definierten Referenzpunkten. Das Vokabular bleibt
   geschlossen, weil die Zeichenschicht (Blütenkarte, Farbpunkte) genau diese 10
   kennt (`frontend/src/colours.ts`, `garden/observations.py::DRAWABLE`).
4. **Primär** = flächengrößtes Cluster über einer Deckungsschwelle. **Sekundär**
   = zweites Cluster, nur wenn es (a) einen Mindestflächenanteil hat (z. B. ≥ 20 %)
   und (b) eine *andere* Vokabelfarbe ist. Sonst bleibt sekundär leer — eine
   einfarbige Blüte hat keine Sekundärfarbe, und eine erfundene wäre dieselbe
   Unehrlichkeit wie eine „0" für unbekannt.
5. **Über mehrere Bilder aggregieren:** pro Art N Fotos annotieren, per Mehrheit
   entscheiden. Das dämpft ein einzelnes schlechtes Foto und liefert zugleich die
   Konfidenz (Einigkeit der Bilder).

## 1.5 Vokabular, Schema und Provenienz

- **Primärfarbe:** in `flower_colour` schreiben — derselbe Schlüssel wie GIFT,
  neue Quelle. Das nutzt genau die Stärke des Schemas: der Primärschlüssel von
  `trait` enthält `source`, also **koexistiert** der Bildwert neben GIFTs Wert,
  statt ihn zu überschreiben, und die Uneinigkeit bleibt sichtbar
  (`resolve_trait` zeigt sie).
- **Sekundärfarbe:** neuer Schlüssel `flower_colour_secondary`. In
  `KNOWN_TRAIT_KEYS` (`data/traits.py`) aufnehmen, sonst wirft `resolve_trait`.
  Die Zeichenschicht und `PlantSummary` (`schemas.py`) müssen ihn kennen —
  Frontend-Client-Typen werden aus dem OpenAPI neu generiert (das CI-Gate dafür
  existiert schon).
- **Quelle/Lizenz/Konfidenz:** `source="image-annotation"` (oder
  `"commons-vision"`), `license` = die Lizenz des/der genutzten Bilder bzw.
  `"derived"` mit gespeicherter Bild-Attribution; `confidence` aus
  Cluster-Trennschärfe × Maskenqualität × Bild-Einigkeit (0–1).
- **Rang:** in `source_rank` (`data/traits.py`) **unter** GIFT/EIVE einordnen —
  ein aus Fotos abgeleiteter Wert ist schlechter als ein publizierter Datensatz,
  aber besser als eine Handeingabe (`manual`). Also ein eigener Rang zwischen
  `SOURCE_PRIORITY` und `MANUAL_SOURCE`. Das ist eine bewusste Entscheidung und
  gehört mit einem Test festgehalten (wie `test_manual_colours` es für `manual`
  tut).

## 1.6 Wo es läuft und was ausgeliefert wird

- Ein neuer Ingest-Adapter `ninanatur/ingest/sources/flower_colour_vision.py`,
  der `Source.run(conn) -> int` implementiert und **nur** über
  `upsert_trait` schreibt — dieselbe Regel wie jeder Adapter.
- Farbe ist **Katalogdaten** (statisch, aus offenen Quellen abgeleitet), also in
  `CATALOGUE_TABLES` schon abgedeckt (`trait`) und über `export-catalogue` ins
  Image. **Nicht** wie `species_info` auf dem Volume — der Unterschied ist
  Lebenszyklus: die Farbe einer Art ändert sich nicht pro Deployment.
- Die Modelle laufen einmalig/gebatcht lokal; die Bild-Bytes werden über
  `ingest/http.py` gecached, ein Rerun kostet keine Downloads.

## 1.7 Validierung — das Tor, bevor irgendein Wert vertraut wird

Die 590 GIFT-Farben sind die **Grundwahrheit**: die Pipeline auf denselben Arten
laufen lassen, ohne die GIFT-Farbe zu sehen, und die Primärfarbe vergleichen.
- Metrik: Anteil exakter Treffer und „ein Nachbar daneben" (violett↔blau,
  rosa↔rot sind die erwartbaren Verwechslungen).
- **Akzeptanzschwelle vor dem Ausrollen festlegen** (z. B. ≥ 80 % exakt auf der
  Hold-out-Menge), sonst nur als niedrig-Konfidenz-Vorschlag mit menschlicher
  Sicht. Das ist derselbe Reflex wie überall im Projekt: erst messen, was die
  Daten hergeben, dann bauen.
- Der Validierungslauf ist ein Test/Skript, das die Zahl ausgibt — er gehört in
  den Bericht des Features, nicht in die CI (er braucht die Modelle).

## 1.8 Risiken, benannt

- **Weiße und gelbe Blüten** über- bzw. unterrepräsentiert je nach Belichtung;
  die Weiß-Kappung in 1.4 ist dagegen, muss aber an der Hold-out-Menge geprüft
  werden.
- **Zuchtformen/Varianten:** ein Foto einer roten Gartensorte einer wild rosa
  Art. Der Katalog führt keine Cultivare (`schemas.py`, `PlantingCreate`), die
  Wikimedia-Fotos aber schon — die Aggregation über viele Bilder + der Rang
  unter GIFT dämpfen das.
- **Falsches Bild in der Kategorie** (Insekt, Habitat, Karte): DINO-Score und
  Maskenqualität filtern, aber nicht perfekt — die Bild-Einigkeit ist der
  Rückfall.
- **Lizenz-Sorgfalt:** ein Bild ohne klare offene Lizenz wird übersprungen; die
  gespeicherte Attribution muss zur tatsächlich genutzten Datei passen.

---

# Teil 2 — Merkmalsextraktion aus Wikipedia-Texten

## 2.1 Was fehlt, und was Text füllen kann

Aus der Tabelle oben: Wuchshöhe (44 %), Blütezeit (41 %), Nährwert/Feuchte/pH/
Licht (48–49 %, aber nur als Ellenberg-Zahl) haben echte Lücken *und* könnten
einen zitierbaren Beleg gebrauchen. Die deutsche Wikipedia trägt das im Fließtext
— und zwar erstaunlich regelmäßig.

**Stichprobe (2026-09-07), deutsche Wikipedia, Abschnitts- und Satzstruktur:**
- *Acker-Witwenblume*: Abschnitte `Vegetative Merkmale`, `Ökologie`, `Vorkommen`.
  Sätze: „Wuchshöhen von 30 bis 80 Zentimetern erreicht.", „Zeigerwerte nach
  Landolt et al. …".
- *Silberdistel*: `Erscheinungsbild und Blatt`, `Ökologie`, `Standort`,
  `Verbreitung`. Satz: „Wuchshöhe von bis zu 40 Zentimetern.".
- Redirects wissenschaftlich→deutsch funktionieren (`Salvia pratensis` →
  *Wiesensalbei*, 200), was den Join auf unseren `canonical_name` trägt.

Die Phrasen sind regelmäßig genug, dass ein Großteil mit Regeln geht, und der
Rest mit einem strukturierten Extraktor.

## 2.2 Die Textquelle

- `action=query&prop=extracts&explaintext=1&titles=<Name>` → Klartext des
  Artikels, **abschnittsweise** (mit `exsectionformat=wiki` bleiben Überschriften
  erhalten). Klartext, nicht HTML — nichts wird als Markup interpretiert.
- Ziel-Abschnitte: `Vegetative Merkmale`/`Erscheinungsbild` (Höhe),
  `Blütenstand und Blüte`/`Generative Merkmale` (Blütezeit, Farbe in Worten),
  `Ökologie`/`Standort`/`Vorkommen` (Böden, Licht, Zeigerwerte).
- Name→Artikel über den wissenschaftlichen Namen mit `redirects=1`; robuster über
  Wikidata `P846` (GBIF-ID) → Sitelink dewiki, damit Homonyme/Schreibweisen nicht
  danebengreifen.
- Gecached über `ingest/http.py` wie jede Quelle. Die **Revisions-ID** (`revid`)
  mitspeichern — sie ist der exakte Beleg-Stand und macht den Extrakt
  reproduzierbar.

## 2.3 Zwei Extraktionsstrategien, zusammen

1. **Regelbasiert (Regex) für die regelmäßigen Phrasen** — hohe Präzision,
   billig, kein Modell:
   - Höhe: `Wuchshöhe[n]? von (\d+) bis (\d+) (Zentimeter|cm|Meter|m)`,
     `bis zu (\d+) …` → `height_max_m` (Einheit normalisieren).
   - Blütezeit: `Blütezeit … von (Monat) bis (Monat)` → `flowering_start/end_month`
     (die Monatsnamen-Abbildung existiert schon in `ingest/sources/gift.py`).
   - Zeigerwerte: „Zeigerwerte nach Landolt/Ellenberg …" → Beleg-Anker für Licht/
     Feuchte/Nährwert.
2. **Strukturierter LLM-Extraktor für den langen Schwanz** — pro Art der
   Zielabschnitt plus ein **striktes JSON-Schema** (Feld → Wert **und der
   Beleg-Satz**). Der Zwang, den Quellsatz mitzuliefern, ist die Provenienz:
   kein Satz, kein Wert. Lokales Modell oder API; wenn API, dann **Ingest-Zeit,
   gebatcht, gecached** — nie auf dem Serving-Pfad, nie im Image.

Regex zuerst, LLM nur wo Regex nichts fand — das hält Kosten und Halluzination
klein und die Präzision hoch.

## 2.4 Die Lizenzentscheidung — CC-BY-SA ist der Haken

Wikipedia-Text ist **CC-BY-SA-4.0**, restriktiver als die CC-BY/CC0-Quellen, auf
denen die Lizenzposition des Projekts steht (`CLAUDE.md`). Die Auflösung:
- Eine **Tatsache** (eine Art wird 30–80 cm hoch) ist nicht urheberrechtlich
  geschützt — der *Wert* darf gespeichert und ausgeliefert werden, mit
  `source="wikipedia-de"`, `license="CC-BY-SA-4.0"` als Herkunftskennung und
  einem Link auf den Artikel/die Revision.
- Der **Beleg-Satz** ist Text und *ist* CC-BY-SA. Er wird zur Prüfung/Review
  gebraucht, gehört aber **nicht in den ausgelieferten Katalog** (oder nur klar
  als CC-BY-SA markiert und von der Export-Lizenzfilterung erfasst). Also: Wert +
  Link ins Image, Beleg-Satz in eine Ingest-Zeit-Tabelle, die nicht in
  `CATALOGUE_TABLES` steht.
- Das ist genau die Sorte Entscheidung, die `CLAUDE.md` meint, wenn es sagt, die
  Herkunft sei das, was „die Lizenzposition verteidigbar hält". Sie muss im
  Feature-Doc explizit stehen, nicht implizit im Code.

## 2.5 Schema, Rang, Deckungsgewinn

- **Wo derselbe Trait schon existiert** (Höhe, Blütezeit), in denselben
  `trait_key` schreiben, neue Quelle — Koexistenz neben GIFT über den
  `source`-im-Primärschlüssel, `resolve_trait` arbitriert.
- **Rang** in `source_rank`: unter EIVE/GIFT (gemessene, publizierte Daten),
  über der Bild-Ableitung und `manual`. Ein Wikipedia-Wert füllt eine Lücke,
  bis ein Datensatz sie füllt, und tritt dann zurück — dasselbe Muster wie
  `manual`.
- **Neue Schlüssel** nur, wo es sie noch nicht gibt (z. B. ein Prosa-belegter
  Boden-/Standort-Text, falls gewünscht) — mit Eintrag in `KNOWN_TRAIT_KEYS`.
- **Erwarteter Gewinn:** Wikipedia-DE-Deckung ~70 % der Kernarten (Stichprobe),
  davon ein hoher Anteil mit Höhe/Blütezeit im Text — das hebt die 41–44 %-Deckung
  spürbar und liefert erstmals einen zitierbaren Beleg statt nur der
  Ellenberg-Konvention.

## 2.6 „Wann säen" — die ehrliche Lücke

Aussaat/Vorkultur ist **gärtnerisch**, nicht botanisch; Wikipedia trägt es nicht
verlässlich, und der Katalog hat es nirgends. Optionen, nach Ehrlichkeit geordnet:
1. **Ableiten und als abgeleitet kennzeichnen:** aus `lifecycle` + `flowering`
   eine grobe Aussaat-Fensterregel (Einjährige: Frühjahr; Stauden: Herbst/
   Frühjahr). `source="derived"`, niedrige Konfidenz, klar als Faustregel benannt
   — kein gemessener Wert.
2. **Eine eigene offene gärtnerische Quelle** suchen (Lizenz zuerst prüfen, wie
   bei jeder Quelle — `robots.txt` **und** Lizenz, nie NaturaDB o. ä.). Erst wenn
   eine offen lizenzierte existiert, wird es ein echter Trait.
Bis dahin: als „nicht belegbar" führen und **nicht** erfinden — dieselbe Regel,
die Farbe bei 6,6 % ehrlich hält.

## 2.7 Validierung — dasselbe Tor

Für Höhe und Blütezeit hat GIFT bereits Werte: Extraktion auf denselben Arten
laufen lassen, GIFT verdecken, vergleichen (Höhe mit Toleranz, Blütezeit auf den
Monat). Erst wenn die Übereinstimmung eine gesetzte Schwelle hält, wird der
Extraktor den unbelegten Arten zugetraut. Ein Skript, das die Zahl ausgibt.

---

## Teil 3 — Gemeinsame Infrastruktur und Reihenfolge

**Beide Pipelines teilen:**
- Schreiben nur über `provenance.upsert_trait` (wirft ohne vollständige
  Provenienz).
- Ausgehende Aufrufe (Commons, Wikipedia, Wikidata, Bild-Bytes) durch
  `ingest/http.py` — Disk-Cache, Delay, Retry; Rerun kostet null Requests.
- Namensauflösung über den bestehenden GBIF-Join; für Wikimedia/Wikidata ist
  `P846` (GBIF-ID) der stabilste Schlüssel.
- Export in den ausgelieferten Katalog über `export-catalogue`/`sync_catalogue`;
  neue `trait_key`s brauchen keinen Schema-Change (die `trait`-Tabelle ist
  schlüssel-generisch), neue Belegtabellen bleiben aus `CATALOGUE_TABLES` heraus.
- Ein **Validierungs-Tor** gegen vorhandene Grundwahrheit, bevor Werte vertraut
  werden.
- Modelle/LLM sind Ingest-Extras, nie Laufzeit — das Image bleibt ~10 MB Katalog.

**Reihenfolge (MDD: Doc → Test → Code, Branch pro Feature nach `dev-deployment`):**
1. **Textextraktion, regelbasiert, Höhe + Blütezeit** — größter, billigster,
   messbarster Deckungsgewinn; validiert direkt gegen GIFT.
2. **Textextraktion, LLM-Schwanz + Standort/Boden-Belege** — mit der
   CC-BY-SA-Entscheidung aus 2.4 im Doc.
3. **Farb-Pipeline, Primärfarbe** — Commons-Bildquelle, DINO+SAM, Lab-Cluster,
   validiert gegen die 590 GIFT-Farben.
4. **Sekundärfarbe** — neuer Schlüssel, Frontend-Typen neu generiert, Zeichen-
   und Vokabularschicht erweitert.
5. **Aussaat** — nur wenn eine offen lizenzierte Quelle gefunden ist, sonst als
   abgeleitete Faustregel klar gekennzeichnet.

**Was ausdrücklich gilt:** keine Quelle ohne `robots.txt`- **und**
Lizenzprüfung; nie NaturaDB oder eine vergleichbare kuratierte Datenbank
(deutsches Datenbankrecht, `CLAUDE.md`); jeder Wert mit Provenienz oder gar nicht.
