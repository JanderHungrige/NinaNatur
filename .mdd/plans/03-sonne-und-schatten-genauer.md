# Plan — Sonne und Schatten, genauer

> Das Licht-/Schattenmodell im Detail gelesen (`ninanatur/solar/*`,
> `garden/lightgrid.py`, `lightcells.py`, `lightview.py`, `roofs.py`,
> `roofshape.py`, `canopies.py`, `slopes.py`, `geo/horizon.py`), seine eigenen
> Known-Issues aus den Docs 64–84 eingesammelt und zwei Fehlerquellen am
> 2026-09-07 **gemessen** statt vermutet. Ergebnis: das Modell ist geometrisch
> sorgfältig und in der Reihenfolge seiner Annahmen ehrlich — aber es misst die
> falsche Größe (Stunden direkter Sonne statt Beleuchtung), es kennt keinen
> Himmel (kein Diffuslicht), und an zwei Stellen ist seine Geometrie messbar
> falsch (konvexe Hülle, Kronen als Zylinder). Nichts davon ist je gegen die
> Wirklichkeit geprüft worden. Der Plan ordnet die Verbesserungen nach
> gemessenem Effekt, und er beginnt mit dem Messgerät.

---

## 1. Das Modell heute — was es tut, Schicht für Schicht

| Schicht | Wie | Wo |
|---|---|---|
| Sonnenstand | NOAA-Algorithmus, UTC, ohne Refraktion, < 1° genau | `solar/position.py` |
| Abtastung | 1. März – 31. Okt., **jeder 10. Tag, alle 30 min**; Monatsansicht jeder 5. Tag | `solar/light.py` (`DAY_STEP`, `MINUTE_STEP`) |
| Untergrenze | Sonne ≤ **5°** zählt nicht (`MIN_ALTITUDE`) | `solar/shading.py` |
| Schatten | Grundriss entlang der Gegensonne verschoben, **konvexe Hülle** aus Original und Kopie | `shading.py::shadow_polygon` |
| Gebäude | Prisma auf `shading_height` = Traufe + `RISE_KEPT[Dachform]` × Aufbau; Dach als Fläche nur für Zellen *auf* dem Dach | `roofs.py`, `roofshape.py`, `lightcells.py` |
| Bäume | **Zylinder** vom Boden bis zur Spitze, Kronenradius aus Höhe geschätzt, Transmission 0,20 / 0,08 / 0,75 (belaubt / immergrün / kahl), Laub Mai–Okt | `garden/canopy.py`, `canopies.py`, `lightview.py` |
| Gelände | Zelle auf eigener Höhe, Hindernis auf dem Grund unter seinem Grundriss, Hangring pro Zelle, Horizontring 5 km / 20 m | `ground.py`, `slopes.py`, `geo/horizon.py` |
| Gitter | 0,5–5 m nach Zeitbudget 5 s; Beet = **Mittel** seiner Zellen | `lightgrid.py` |
| Ergebnis | Sonnenstunden/Tag → Ellenberg L über eine **Stufentabelle** (`SUN_HOUR_BANDS`, „a convention, not a measurement") | `solar/light.py` |
| Warnung | Pflanze vs. Standort, Toleranz 2 L-Stufen | `garden/misplaced.py` |

**Was bestätigt ist und bleibt:** die Sonnenstand-Konventionen sind getestet
(Äquinoktium, Solstitien, Ost→Süd→West), die Projektion stimmt mit einem
3D-Strahl überein (`test_shading_is_ray_tracing.py`), Hochbeete stehen über
Zäunen, Nord-/Südpitch eines 38°-Satteldachs unterscheiden sich messbar
(10,2 h gegen 11,7 h, Wave 21). Die Reihenfolge *Nutzer > Vermessung > Messung
> Annahme* ist überall gesagt. Das ist die Basis, nicht das Problem.

---

## 2. Fehlerquellen, gemessen und geordnet

Nach Größe des Effekts, mit dem, was am 2026-09-07 dazu gemessen wurde.

### E1 — Die konvexe Hülle löscht Innenhöfe · **groß, gemessen**

`shadow_polygon` nimmt die konvexe Hülle. Für ein L- oder U-förmiges Haus ist
das nicht „leicht großzügig" (so das Docstring), sondern falsch:

| Punkt in der L-Kerbe (10×10 m Haus, 9 m hoch, 5×5-Kerbe NO) | Hülle | exakt (zwei Rechtecke) |
|---|---|---|
| (2,5, −2,5) | **0,00 h** | **3,98 h** |
| (3, −4) | **0,00 h** | 2,82 h |
| (8, 3) außerhalb | 9,78 h | 10,14 h |

Ein Beet im Winkel eines L-Hauses — die klassische geschützte Ecke — bekommt
laut Modell **keine Sonne**, tatsächlich vier Stunden. Genau diese Grundrisse
liefert der Kartenimport (OSM-Umrisse sind selten Rechtecke), und
`roofshape._oriented_box` legt darauf noch ein Rechteck. Die einzige Stelle,
die es heute richtig macht, ist der LoD2-Pfad, weil er Gebäudeteile getrennt
liefert.

**Fix:** keine Hülle. Entweder (a) den Grundriss in konvexe Teile zerlegen
(Ear-Clipping, dann Hertel–Mehlhorn) und jeden Teil sweepen — kleiner Eingriff,
alles andere bleibt; oder (b) Strahl gegen die Wände des Prismas testen
(Segment-Strahl-Schnitt in 2D plus Höhenvergleich) — exakt für *jedes*
Polygon und die Grundlage für E4. Empfehlung: (b), weil E4 es ohnehin braucht.

**Test:** das L-Haus oben als Regressionstest — 0 h → ≈ 4 h.

### E2 — Nur direkte Sonne, kein Himmel · **groß, konzeptionell**

Das Modell zählt Stunden direkter Sonne. Eine Pflanze erlebt **Beleuchtung**:
direkt *plus* diffus. In Deutschland ist rund die Hälfte der Jahres-Globalstrahlung
diffus (in der Vegetationszeit etwas weniger). Zwei Standorte mit 2 h direkter
Sonne sind daher nicht gleich: ein Nordbeet unter offenem Himmel (Himmelsanteil
~90 %) ist hell, ein Beet unter einer dichten Krone mit einem Sonnenschlitz am
Mittag (Himmelsanteil ~20 %) ist dunkel. Das Modell kann sie nicht auseinanderhalten.

**Und das ist zugleich die Ellenberg-Definition.** L ist bei Ellenberg über die
**relative Beleuchtungsstärke** (r.B., Anteil des Freilandlichts) definiert:
L9 nur bei vollem Licht, selten unter 50 % r.B.; L8 selten unter 40 %; L7 meist
volles Licht, auch bis ~30 %; L6 selten unter 20 %; L5 meist über 10 %;
L3 meist unter 5 %; L1 unter 1 %. `SUN_HOUR_BANDS` ersetzt diese Definition
durch eine Konvention aus Stunden — das Modell sagt selbst, dass es keine
Messung ist. Mit einem Himmelsanteil wird daraus eine Ableitung aus der
Definition.

**Fix:** pro Zelle den **Sky-View-Factor** (SVF) aus derselben Geometrie
berechnen: einen Halbraum in z. B. 145 Tregenza-Flächen (oder 36 Azimute × 8
Höhenbänder) abtasten, jede Richtung mit dem vorhandenen Verdeckungstest
gegen Hindernisse, Hangring und Horizontring prüfen, mit cos(Zenit) × Raumwinkel
gewichten. Das ist derselbe Mechanismus wie `shadow_field`, nur mit 145 statt
~1 200 Richtungen — **billiger** als das Saisongitter. Dann

    r.B. = w_direkt · (direkte Stunden / Freiland-Stunden) + w_diffus · SVF

mit `w_direkt ≈ 0,5`, `w_diffus ≈ 0,5` als dokumentierte Startwerte (E3 macht
daraus Strahlung; eine DWD-Klimatologie könnte sie regional machen, siehe
Entscheidungen). L folgt dann aus Ellenbergs Schwellen, nicht aus einer Tabelle.

**Auf der Seite:** die Sonnenstunden bleiben die physische Zahl, die jemand
mit dem Pflanzenetikett vergleicht. Neu daneben: „sieht 62 % des Himmels" und
die daraus abgeleitete Stufe. Kein Kilowatt, keine Behauptung, die das Modell
nicht tragen kann.

### E3 — Stunden statt Strahlung · **mittel, dokumentiert**

Docs 71 und 72 nennen es selbst: eine Stunde März-Sonne bei 8° Höhe zählt wie
eine Juni-Stunde bei 60°. Ein Nordhang „gewinnt" Stunden, weil er über
Hindernisse hinwegsieht, und bekommt weniger Energie pro Quadratmeter; das Modell
weigert sich zu Recht, den Hang zu *bewerten*, weil es nur Stunden hat.

**Fix:** jede beleuchtete Probe mit einer **Klarhimmel-Direktstrahlung ×
cos(Einfallswinkel auf die Zellfläche)** gewichten. Ein einfaches Klarhimmel­modell
(Haurwitz/Kasten-Czeplak) braucht nur die Sonnenhöhe — keine Daten, keine
Abhängigkeit. Ausgegeben wird **relativ** zum Freiland derselben Lage (dimensionslos),
also weiterhin kein kWh-Anspruch, nur eine richtige Gewichtung. Damit ist der
Hang ehrlich bewertbar (Doc 73 kann „Südhang, 16 %" dann einordnen statt nur
benennen), und die Morgen/Nachmittag-Teilung bekommt physikalische Bedeutung
(Nachmittag heißer).

Wave 21 sagt „Stunden, nicht Energie; ein Solarrechner wäre ein anderes
Projekt". Das bleibt wahr: relative Gewichte sind kein Ertrag.

### E4 — Dächer als „mittlere Höhe" statt als Flächen · **mittel**

`RISE_KEPT` (Satteldach 0,5, Walm 0,4, Pult 0,6, Misch 0,8) ist ein
Formfaktor, kein Dach. Ein Satteldach wirft in Firstrichtung den Schatten der
vollen Firsthöhe, quer dazu den der Traufe — ein Mittelwert ist in beiden
Richtungen falsch, und `roofs.py` nennt `MIX` selbst „die schwächste Zahl".
Die Dachflächen existieren schon (`roofshape.surface_of`), werden aber nur für
Zellen *auf* dem Dach gefragt.

**Fix:** Schatten per Strahl gegen die echten Flächen: zwei Dachebenen plus
Giebeldreiecke plus Wände (E1b). `RISE_KEPT` entfällt für Sattel/Walm/Pult;
`MIX`/`OTHER` bleiben als Prisma. Die Eingaben (Traufe, Firstrichtung aus LoD2)
liefert Wave 21 — dieser Plan ist deren Abnehmer, nicht ihr Ersatz.

### E5 — Kronen als Zylinder · **mittel**

Ein Zylinder vom Boden bis zur Spitze beschattet seinen gesamten Grundriss bei
jeder Sonnenhöhe: direkt unter der Krone — genau da, wo jemand ein Schattenbeet
plant — bleibt nur die Transmission (0,2×). Real ist eine Krone ein Ellipsoid auf
einem Stamm; unter ihr fällt bei mittlerer Sonne Licht *unter* der Krone durch,
und was durch die Krone geht, hängt vom Weg durch sie ab.

**Fix:** Krone = Ellipsoid (Zentrum in Höhe h − r_v, Halbachsen r_h, r_v), Stamm
vernachlässigt; Strahl–Ellipsoid-Schnitt liefert die Weglänge L; Transmission
`T = exp(−k·L)`, mit k so kalibriert, dass ein Weg durch den vollen Durchmesser
die heutigen 0,20 / 0,08 / 0,75 ergibt (also nichts wird schlechter, wo das alte
Modell galt). Neues Feld „Kronenansatz" (Standard ⅓ der Höhe) am Element; der
Kronendurchmesser ist heute schon editierbar (`width`).

### E6 — Abtastung und 5°-Grenze · **klein, gemessen, billig**

Konvergenz gemessen (Haus 9 m, 8 m südlich, Wuppertal):

| Punkt | 30 min / 10 d (heute) | 10 min / 10 d | 10 min / 2 d | 5 min / 1 d |
|---|---|---|---|---|
| (0, 0) | 10,84 h | 10,97 | 11,03 | **11,06** |
| (0, −6) | 5,04 h | 5,16 | 5,23 | **5,26** |

Das heutige Raster liegt **systematisch ~2 % zu niedrig** (≤ 0,22 h). Kein
Drama, aber ein Bias, und der Kommentar „fein genug, dass sich die Antwort nicht
mehr bewegt" ist damit widerlegt — ein Konvergenztest fehlt. Dazu: zwischen 2°
und 5° Sonnenhöhe liegen im Freiland **0,71 h/Tag** (von 12,55 h über 5°), die
das Modell wegwirft; mit dem Horizontring, der reale Verdeckung kennt, kann die
Grenze auf 2–3° sinken (darunter machen Refraktion und Aerosol die Direktsonne
belanglos). Beides erst nach E7, damit es das Budget nicht sprengt.

### E7 — Rechenzeit ist die Währung für alles oben · **Voraussetzung**

Das Feld ist reines Python: pro Moment × Hindernis × Zelle. Das 5-s-Budget
zwingt bei 40 Häusern zu 3-m-Zellen. E1b/E4/E5 verlangen Strahltests, E2 145
Extra-Richtungen, E6 dreimal mehr Momente. Ohne Vektorisierung frisst das die
Auflösung.

**Fix:** pro Moment die Schattenmasken aller Hindernisse als numpy-Boolarrays
auf dem Gitter rastern (Bounding-Box-Ausschnitt, Punkt-im-Polygon vektorisiert),
multiplikativ akkumulieren; Strahltests batchweise pro Moment für alle Zellen.
Erwartung: eine Größenordnung. Dazu gehört die Prozess-Auslagerung aus Plan 01
(ST-03), damit die Rechnung den Threadpool nicht blockiert.

### E8 — Kleinere, benannte Ungenauigkeiten

- **Phänologie:** Laub von Monat 5 bis 10 für alle Laubbäume; der Austrieb liegt
  in Deutschland meist Ende April (Buche ~25. April ± 10 Tage), also zählt der
  April als kahl. Optional: DWD-Phänologie (offene Daten, Stationen) je Region.
- **Nahfeld-Gelände:** Doc 71 — eine Böschung zwischen Zelle und Sonne schattet
  nur, wenn etwas darauf steht. Fix: Ray-Marching durch das 100-m-Fenster
  (1 m Zellen, ≤ 100 Schritte), nur wo Hang > 5°.
- **Beet = Mittelwert:** ein Beet mit sonnigem Süd- und schattigem Nordrand
  meldet Halbschatten. Ausgeben: Anteile (Sonne / Halbschatten / Schatten) und
  Min/Max — „Nordrand halbschattig" ist eine Aussage, 6,4 h ist keine.
- **Uhrzeit der Tagesframes:** die Frames tragen UTC-Minuten und werden heute
  nirgends als Uhrzeit angezeigt (geprüft: kein `minute`-Leser im Frontend).
  Sobald eine Uhr dazukommt, muss sie nach `Europe/Berlin` umrechnen — sonst
  steht der Mittagsschatten um 14 Uhr.
- **Nicht modelliert und so zu benennen:** Reflexion (helle Wände), Halbschatten
  (Penumbra), Bewölkung (siehe Entscheidungen).

---

## 3. Das Messgerät zuerst: Validierung

Nichts oben ist bisher gegen etwas anderes als sich selbst geprüft. Drei Ebenen,
in dieser Reihenfolge gebaut, **bevor** das Modell angefasst wird — sonst ist
„genauer" eine Behauptung:

1. **Sonnenstand gegen eine Referenz.** `pvlib` (BSD) als *Dev-Extra*, ein Test
   über 200 zufällige Momente und Orte in Deutschland: Höhe und Azimut auf < 0,5°.
   Findet Konventionsfehler, die die Plausibilitätstests nicht sehen.
2. **Geometrie gegen einen Strahl.** `test_shading_is_ray_tracing.py` erweitern:
   zufällige *konkave* Grundrisse, Dachflächen, Ellipsoide — der 2D-Test muss mit
   einem 3D-Strahltest übereinstimmen. Das L-Haus aus E1 als fester Fall.
3. **Wirklichkeit.** Ein Feature *„Schatten kalibrieren"*: der Gärtner markiert
   auf dem Plan, wo die Schattenkante seines Hauses *jetzt* (Datum, Uhrzeit)
   fällt; das Modell zeichnet seine Vorhersage daneben und nennt den Abstand.
   Das ist billig, ehrlich, und fängt zugleich falsche Höhen, falsche Nordung und
   falsche Anker — die drei Fehler, die kein Test sieht. Ergänzend einmalig: ein
   synthetischer Fall gegen ein unabhängiges Werkzeug (z. B. eine Sonnenstudie in
   Blender) im Feature-Doc dokumentiert, nicht automatisiert.

Dazu die **Konvergenzsuite** (E6): Raster halbieren, Beetwert darf sich um
< 0,2 h bewegen — als Test, der bei jeder Modelländerung mitläuft.

---

## 4. Umsetzungsreihenfolge

Doc → Test → Code, Branch pro Feature nach `dev-deployment`. Jede
Modelländerung erhöht eine `MODEL_VERSION`, die in `signature_of` eingeht —
sonst zeigen gespeicherte Gitter alte Antworten ohne `stale`.

| # | Feature | Effekt | Hängt an |
|---|---|---|---|
| 0 | Validierungs-Harness (Abschnitt 3, Ebenen 1–2, Konvergenz) | Messbarkeit | — |
| 1 | **E1b** Strahl gegen Wände, Hülle raus | 0 h → 4 h in der L-Kerbe | 0 |
| 2 | **E7** Vektorisierung + Prozesspool | Budget für alles weitere | Plan 01 ST-03 |
| 3 | **E6** 10 min / 5 d, Untergrenze 3° | +2 %, ehrlicher Rand | 2 |
| 4 | **E2** SVF + relative Beleuchtung + Ellenberg-Schwellen | neue Größe auf der Seite | 2 |
| 5 | **E3** Strahlungsgewichtung (relativ) | Hang/Morgen bewertbar | 4 |
| 6 | **E4** Dachflächen als Schattenwerfer | `RISE_KEPT` raus | Wave 21, 1 |
| 7 | **E5** Ellipsoid-Kronen | Schattenbeete unter Bäumen | 1 |
| 8 | Ebene 3: „Schatten kalibrieren" | Wirklichkeit im Produkt | 4 |
| 9 | E8-Punkte nach Bedarf | — | — |

**Aufwand, grob:** 0–1 je 1–2 PT; 2 etwa 3 PT; 3 ½ PT; 4 etwa 3 PT (inkl. UI
und Doc); 5 1–2 PT; 6 2–3 PT; 7 2 PT; 8 2–3 PT (mit UI). Zusammen etwa
drei Wochen, wobei 0–4 den größten Teil des Nutzens tragen.

---

## 5. Entscheidungen für den Owner

1. **Was steht als Hauptzahl auf der Seite?** Sonnenstunden (vergleichbar mit
   dem Etikett) oder relative Beleuchtung (näher an Ellenberg)? Empfehlung: beide,
   Stunden groß, Himmelsanteil und L daneben.
2. **Regionale Bewölkung ja/nein?** Der DWD stellt Monatsraster der
   Globalstrahlung offen bereit (Attribution nach GeoNutzV). Damit würde aus
   „mögliche Sonne" „erwartbare Sonne" (Freiburg ≠ Kiel). Eine Quelle mehr in
   der Registry, wie Wave 17 sie führt. Nicht nötig für E2–E3, aber der Schritt
   danach.
3. **Werte werden sich verschieben.** E2/E3 ändern L-Werte bestehender Gärten
   beim nächsten Neuberechnen. Das gehört auf die Seite gesagt („Modell v2,
   berechnet am …"), nicht stillschweigend.
