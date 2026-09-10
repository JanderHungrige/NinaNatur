# Plan — Höhendaten für die Lücken

> Frage: gibt es eine umsetzbare Lösung für die fehlenden Höhendaten? **Ja,
> und sie ist besser als erwartet.** Zwei Dinge haben sich seit Wave 17
> (2026-09-05) geändert bzw. wurden damals nicht gefunden, und beides wurde am
> 2026-09-07 mit echten Anfragen geprüft:
>
> 1. **Alle 16 Bundesländer geben ihr DGM1 inzwischen offen ab.** Den acht
>    Ländern, die in der Registry fehlen, fehlt nur ein *Dienst mit
>    Ausschnitt* (WCS) — nicht die Daten. Bayerns Kachel-URL antwortet anonym
>    (200, 2,5 MB pro km²). Das ist genau die „sekundäre Stufe", die der
>    Wave-17-Plan vorgesehen und nie gebaut hat.
> 2. **LoD2-Gebäudemodelle sind in praktisch jedem Land offen** — mit
>    gemessener Höhe *und* Dachform, also besser als jedes Oberflächenmodell.
>    Bayerns LoD2-Kachel antwortet anonym (200, 161 MB pro km²).
>
> Dazu zwei bundesweite Rückfallquellen für den Horizontring, beide anonym
> geprüft: Copernicus GLO-30 (30 m, 32 MB pro 1°-Kachel, per HTTPS) und BKGs
> DGM200-WCS.

---

## 1. Was heute fehlt, und was ein Garten dadurch verliert

| Land | Gelände (WCS) | Oberfläche | LoD2 | Der Garten verliert |
|---|---|---|---|---|
| NW, BB, BE, ST, NI, MV, HE | ✔ | ✔ | nur NW | Dachformen (außer NW) |
| BW | ✔ (ganze Meter) | 5 m — abgelehnt | — | Gebäudehöhen, Bäume, Dachformen |
| **BY, RP, SN, TH, SH, HH, HB, SL** | — | — | — | **alles**: Relief, Hang, Horizont, gemessene Höhen, gefundene Bäume, Dachformen |

Die acht Länder ohne Eintrag sind rund **36 % der Bevölkerung** (Doc 68). Ein
Garten in München, Mainz, Dresden, Kiel oder Hamburg bekommt heute die flache
Welt von vor Wave 17 und Häuser mit angenommener Höhe.

---

## 2. Quellen, verifiziert am 2026-09-07

Status: **✔ geprüft** = eigene Anfrage hat geantwortet; **✔ belegt** = Portal-/
Katalogseite gelesen, Abrufmuster noch nicht getestet; **?** = zu prüfen.

### Gelände (DGM1) — die acht fehlenden Länder

| Land | Abgabe | Lizenz | Status |
|---|---|---|---|
| **Bayern** | 1×1-km-GeoTIFF, direkte URL `https://download1.bayernwolke.de/a/dgm/dgm1/{E}_{N}.tif` (UTM32 in km, z. B. `690_5334`), Index je Gemeinde als Metalink `…/odd/a/dgm/dgm1/meta/metalink/{AGS}.meta4` mit SHA-256 | CC-BY-4.0, „Datenquelle: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de" | **✔ geprüft** (200, 2 558 672 B) |
| Thüringen | Atom-Feed / DLA-Download-Client (`geoportal.geoportal-th.de/gaialight-th/_apps/dladownload/dl-dhm.html`), DGM1 2014–2019 | dl-de/by-2-0 | ✔ belegt |
| Sachsen | 2×2-km-Zips, Batch-Download `geodaten.sachsen.de/downloadbereich-digitale-hoehenmodelle-4851.html`, DGM1 **und DOM1** | dl-de/by-2-0 | ✔ belegt |
| Schleswig-Holstein | 1×1-km-Kacheln, Download-Client `geodaten.schleswig-holstein.de/gaialight-sh/_apps/dladownload/dl-dgm1.html`, NoData −9999 | offen (LVermGeo SH) | ✔ belegt |
| Hamburg | Transparenzportal, Datensatz „Digitales Höhenmodell Hamburg DGM 1" | offen (Transparenzportal) | ✔ belegt |
| Bremen | GeoPortal Bremen / MetaVer, kostenfrei seit 2024-06-09 | offen | ✔ belegt |
| Rheinland-Pfalz | Geoshop Open Data (`lvermgeo.rlp.de/geodaten-geoshop/open-data`), DGM seit 2016 frei | offen | ✔ belegt |
| Saarland | Download-Portal des LVGL; **Achtung:** der WCS verbietet das Einbinden (Doc 68), der Download ist laut Katalog dl-de/by-2-0 — nur der Download darf genutzt werden, Lizenztext bei Feature 0 einholen | dl-de/by-2-0 (Download) | ? |

Hintergrund: OpenDTM-DE (opendem.info) führt alle 16 Länder zusammen und nennt
Juni 2024 als Stand, ab dem jedes Land ein offenes hochauflösendes Modell hat.
Sein eigenes Produkt (40-km-Kacheln, Gigabytes) ist für einen Garten-Fetch
ungeeignet — aber es ist der Beleg, dass die Lücke eine Abgabe-, keine Datenlücke ist.

### Gebäude (LoD2, CityGML) — gemessene Höhe *und* Dachform

| Land | Abgabe | Lizenz | Status |
|---|---|---|---|
| **Bayern** | Kachel-URL `https://download1.bayernwolke.de/a/lod2/citygml/{E}_{N}.gml` | CC-BY-4.0 | **✔ geprüft** (200, 161 627 079 B) |
| Baden-Württemberg | Open-GeoData-Portal, CityGML, ~50 MB je Gemeinde; „in der Regel Open Data" (Einzelbestellungen kosten Service-Entgelt); Dachtyp automatisch klassifiziert (~90 %) | offen (LGL) | ✔ belegt |
| Rheinland-Pfalz | Geoshop Open Data, ~3,5 Mio. Gebäude, CityGML | offen | ✔ belegt |
| Sachsen | 2×2-km-Kacheln, CityGML/3D-DXF/3D-Shape | dl-de/by-2-0 | ✔ belegt |
| Thüringen | 2×2-km-Kacheln, Atom-Feed `geoportal.geoportal-th.de/dienste/atom_th_gebaeude` | dl-de/by-2-0 | ✔ belegt |
| Hessen | opendata.hessen.de „3D-Gebäudemodell HE LoD2" | offen | ✔ belegt |
| Niedersachsen | OpenGeoData-Portal, landesweit seit 2019 | offen | ✔ belegt |
| Sachsen-Anhalt | Download, bis 5 Kacheln je Anfrage | offen | ✔ belegt |
| Berlin | Berlin Open Data | offen | ✔ belegt |
| Schleswig-Holstein | OpenGBD, CityGML/Shape | offen | ✔ belegt |
| Mecklenburg-Vorpommern | GeoPortal MV, Dienste | ? Lizenz prüfen | ? |
| Hamburg | Transparenzportal (CityGML-Suche vorhanden) | offen | ✔ belegt |
| Bremen | Landesweite Zips (Doc 80) | offen | ✔ belegt |
| Brandenburg | ? | ? | ? |
| Saarland | „sukzessive" angekündigt | ? | ? |
| **Bund: LoD2-DE (BKG)** | ein bundesweites Produkt; Doku-PDF war am 2026-09-07 nicht erreichbar (404) | ? | **? — zuerst prüfen** |

**Warum das die wichtigere Hälfte ist:** ein LoD2-Gebäude bringt Höhe (±1 m),
Dachform, Traufe und Firstrichtung — alles, was Wave 19/21 aus nDOM und
OSM-Stockwerken mühsam schätzt. Für Gebäude schlägt LoD2 jedes Oberflächenmodell;
das nDOM/DOM bleibt für **Bäume** (`canopies_in`) und als Prüfung nötig.

### Bundesweite Rückfallquellen

| Quelle | Wofür | Status |
|---|---|---|
| **Copernicus DEM GLO-30** — 30-m-COG je 1°×1°, anonym per HTTPS (`copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N51_00_E007_00_DEM/….tif`) | **Horizontring überall** (5 km bei 20–30 m); grobe Hangrichtung | **✔ geprüft** (200, 31,9 MB) |
| BKG DGM200 INSPIRE-WCS (`sgx.geodatenzentrum.de/wcs_dgm200_inspire`) | Horizontring, gröber | **✔ geprüft** (Capabilities) |
| EUBUCCO v0.1 (Zenodo) — 200 Mio. Gebäude EU, Höhe für 73 %, DE aus LoD-Daten | Gebäudehöhen als Rückfall | ✔ belegt; **ODbL** (Share-alike) — Attribution, nur ableiten, nie weitergeben |
| Overture Maps buildings | Höhen in DE dünn | ✔ belegt; ODbL; niedrige Priorität |
| basemap.de 3D (BKG) | 3D-Tiles ohne Attribute (Doc 80) | nicht adoptiert |

Copernicus GLO-30 ist die Antwort auf „Horizont für die neun Länder ohne Dienst":
ein Berg braucht keine Meterauflösung, der Ring wird heute bei 20 m gemessen, und
die Kachel ist eine Datei, die einmal je Gradzelle auf das Volume kommt.
Lizenz: Copernicus-DEM-Bedingungen (kostenfrei, Namensnennung DLR/Airbus/ESA) —
Text bei Feature 0 aus der Quelle übernehmen, wie `attribution` es überall verlangt.

---

## 3. Architektur: die Kachel-Stufe

Wave 17 hat sie benannt und begründet (*primär WCS-Ausschnitt, sekundär
Kachel-Download nur wo es keinen Dienst gibt, tertiär nichts*). Sie fehlt.

- **`TileSource`-Registry** neben `TerrainSource`/`SurfaceSource`
  (`geo/tile_sources.py`): je Land `state`, `product` (dgm1 | dom1 | lod2),
  `url_for(east_km, north_km)`, `tile_km` (1 oder 2), `licence`, `attribution`,
  `vertical_step_m`, Format-Hinweise (GeoTIFF / Zip / GML). Gleiche Testregel wie
  Doc 68: kein Eintrag darf kostenpflichtig sein, jeder braucht eine Attribution.
- **Kachelname berechenbar** wie NRWs `lod2.tile_name`: aus UTM32/33 in km.
  Wo ein Portal nur einen Index oder Atom-Feed bietet (TH, SH, HH, HB, RP), wird
  der Index einmal geholt, gecached und daraus die Kachel-URL aufgelöst.
- **Fetch über `ingest/http.py`** (`get_bytes`), **Cache auf dem Volume** und mit
  Größenkappe — nicht im Container-Layer, siehe Plan 01 ST-07. Höflichkeit:
  eine Kachel je Ort je Produkt, `REQUEST_DELAY_S` großzügig, User-Agent mit
  echtem Kontakt (Plan 01 S-20).
- **Zuschneiden, nicht behalten:** GeoTIFF-Kacheln (2,5–5 MB) auf das 200-m-Fenster
  mit dem vorhandenen `read_raster`/`resample`; Zips (SN) im Speicher entpacken;
  LoD2-GML (bis 161 MB) mit dem vorhandenen `iterparse` streamen und **nur die
  Gebäudetabelle** behalten (ein paar hundert Byte je Gebäude) — die Kachel selbst
  darf nach dem Parsen aus dem Cache fallen. NRWs 38-MB-Tile ist das Muster.
- **Provenienz wie gehabt:** `terrain_window.source/licence/attribution`
  tragen die Kachelquelle; die Seite sagt „DGM1 Bayern (CC BY 4.0)".
- **CityGML-Dialekte:** `buildings_from` liest NRW (CityGML 1.0, `bldg:`-Namensraum,
  `measuredHeight`, `roofType` als AdV-Schlüssel, `BuildingPart`s). Andere Länder
  weichen ab (CityGML 2.0-Namensräume, Kodierung der Dachform, Teile). Je Land ein
  kleines Fixture-Fragment im Test, nie die Kachel.
- **Reihenfolge der Wahrheit bleibt:** Nutzer > Vermessung (LoD2) > Messung
  (nDOM) > Annahme — `height_source`/`roof_source` gibt es schon.

---

## 4. Umsetzungsreihenfolge

Nach Bevölkerung und Sicherheit der Quelle. Doc → Test → Code; jedes Feature
mit einem Registry-Test und einem Offline-Fixture; **nichts** davon läuft in
der Test-Suite gegen das Netz (`conftest.py` hält das so).

| # | Feature | Warum zuerst |
|---|---|---|
| 0 | **Registry-Sondierung** wie Doc 68/80: jede Zeile oben mit einer echten Anfrage bestätigen, Lizenztexte und Attributionen sammeln, **LoD2-DE des BKG zuerst prüfen** — wenn es ein bundesweites, offenes, kachelbares Produkt ist, ersetzt es zwölf Adapter | entscheidet die Form von 3 |
| 1 | **Kachel-Stufe + Bayern DGM1** (URL verifiziert, größtes Land, 13 Mio.) | größter Gewinn, kleinstes Risiko |
| 2 | **Copernicus GLO-30 als Horizont-Rückfall überall** (Range-Reads auf das COG oder eine Kachel je Gradzelle auf dem Volume; der eigene TIFF-Leser kann gekachelte TIFFs seit Sachsen-Anhalt) | neun Länder bekommen einen Horizont |
| 3 | **LoD2-Adapter**: BY (verifiziert), BW (macht die 5-m-Lücke für Gebäude zu), RP, SN, TH, SH, HH, HB, dann NI/HE/BB/BE/ST/MV | Dachformen und Traufen ohne Handarbeit — der Rest von Wave 21 |
| 4 | **DOM/DGM-Kacheln** für RP, SN (DOM1 liegt dabei), TH, SH, HH, HB, SL | Bäume (`canopies_in`) in den restlichen Ländern |
| 5 | UI: Quelle und Lizenz je Garten sichtbar; `signature_of` reagiert auf eine neu verfügbare Quelle (Karte wird `stale`) | Ehrlichkeit auf der Seite |

**Aufwand, grob:** 0 etwa 2 PT (es sind Anfragen und Lesen); 1 etwa 3 PT;
2 etwa 2–3 PT; 3 etwa 1 PT je Land nach dem ersten (Dialekte); 4 etwa ½ PT je
Land; 5 etwa 1 PT. Bayern + Copernicus + BW-LoD2 zusammen sind eine Wave.

---

## 5. Risiken und Grenzen

- **Portale ändern URLs ohne Version.** Die Registry braucht einen Sondierungs­test,
  der *manuell* gegen das Netz läuft (Skript, nicht Suite) und im Feature-Doc
  datiert wird — wie „probed on 2026-09-05" in Doc 68.
- **Kachelgrößen.** 161 MB je LoD2-Kachel sind ein Download je Garten-Kilometer;
  die Gebäudetabelle danach ist winzig. Volume-Cache mit LRU und Kappe; nie im Image.
- **Lizenzen sind Attributionen.** Jede Quelle hat einen eigenen Pflichttext;
  ein Garten kann drei tragen (DGM1 Land, LoD2 Land, Copernicus). Die Seite muss
  alle nennen — das Muster existiert (`TerrainOut.attribution`).
- **ODbL (EUBUCCO/Overture)** ist Share-alike. Nur als per-Garten abgeleitete
  Werte auf dem Volume und mit Attribution nutzbar, nie im ausgelieferten Katalog.
  Deshalb nachrangig gegenüber den amtlichen LoD2-Daten.
- **Alte Gärten** (vor 2026-09-07, 0,1°-Anker) bleiben flach — `is_precise`
  gilt für die Kachel-Stufe genauso.
- **Saarland:** WCS-Nutzungsbedingung verbietet das Einbinden; nur der Download
  mit seiner eigenen Lizenz kommt in Frage, und nur mit gelesenem Lizenztext.

---

## 6. Nachfrage: „Wir wollen rund 1 m² Genauigkeit — DGM1 reicht dafür nicht"

*Ergänzt am 2026-09-07 nach Rückfrage des Owners.*

### 6.1 Was DGM1 ist, und was es nie sein wird

DGM1 **ist** ein 1-m-Raster: eine Zelle je Quadratmeter, Höhengenauigkeit
±15–30 cm (Thüringen nennt ±15 cm, NRW ±30 cm). Für das *Gelände* — Hang,
Böschung, Horizont — ist das Ziel damit überall erreicht, wo DGM1 vorliegt
(seit 2024 in allen 16 Ländern, Abschnitt 2). Feiner als 1 m ist beim Gelände
auch nicht sinnvoll: was darunter liegt, ist Gartenbau, kein Relief.

Was DGM1 **nicht** kann, und was ein Garten für seine Schatten braucht, sind die
**Dinge auf dem Gelände**: Häuser, Bäume, Hecken, Mauern, Hochbeete, Schuppen.
Das ist keine Auflösungs-, sondern eine Produktfrage — DGM ist per Definition
„ohne Bewuchs und Bebauung". Die 1 m² gelten also für die *Oberfläche*, und dort
sieht die Treppe so aus:

| Stufe | Quelle | Auflösung | Sieht | Sieht nicht | Wo |
|---|---|---|---|---|---|
| A | nDOM / DOM (Raster) | 0,5 m (NW) · 1 m (7 Länder) · 5 m (BW, abgelehnt) | Höhe je Zelle | *was* es ist; Kronenansatz; Innenstruktur | 8 Länder, gebaut |
| B | **Laserscan-Punktwolke** (LAZ, klassifiziert) | 3–10 Punkte/m² → eigenes Raster 0,5–1 m | Boden / Gebäude / Vegetation getrennt, **Kronenansatz**, Hecken, Mauern ab ~0,5 m | Hochbeet < 30 cm (Rauschen), alles unter dichtem Kronendach | 9 Länder offen (6.2) |
| C | LoD2 | je Gebäude | gemessene Höhe, Dachform, Traufe | nur Gebäude | fast alle Länder (Abschnitt 2) |
| D | bDOM / DOP20 (Bildbasis) | 0,2–0,4 m | Umrisse von Hecken, Kronen, Schuppen auf 20 cm | verlässliche Höhen unter Bewuchs | BY, SH, HH (bDOM); DOP20 fast überall (Wave 8) |
| E | **Eigenmessung mit dem Telefon** | 1–5 cm auf 5 m, drift über den Garten | alles im eigenen Garten inkl. Hochbeet, Zaun, junger Baum | Nachbars Grundstück | jeder Garten, opt-in |

**Die Antwort auf „1 m²":** außerhalb des eigenen Zauns erreichen B + C das Ziel
(Objekthöhen auf 0,5–1 m mit Klassifikation), innerhalb des Zauns nur E. Alles
darüber hinaus (Google/Apple-3D-Meshes, Streetview-Ableitungen) ist nicht
lizenzierbar oder nicht offen und kommt nicht in Frage.

### 6.2 Punktwolken: wer sie offen abgibt (Stand Juni 2026, zu verifizieren in Feature 0)

Aus der gepflegten Übersicht `wiesehahn/lidar_availability_germany` (2026-06-02),
NRW am 2026-09-07 selbst geprüft:

| Land | offen? | Lizenz | Dichte | Bemerkung |
|---|---|---|---|---|
| **Nordrhein-Westfalen** | ✔ | dl-de/zero-2-0 | 4–10 /m² | **✔ geprüft:** `opengeodata.nrw.de/…/3dm_l_las/3dm_32_{E}_{N}_1_nw.laz`, 35 860 Kacheln, Ø 104 MB, max 445 MB, Index als XML |
| Bayern | ✔ (seit 2023) | CC-BY-4.0 | 1–4 /m² | OpenData „Laserdaten"; dünn — 1 m Raster, nicht 0,5 |
| Berlin | ✔ | dl-de/by-2-0 | 10 /m² | LAS 1.4, 2021 |
| Brandenburg | ✔ (seit 2021) | dl-de/zero-2-0 | 5 /m² | LAZ 1.4 |
| Hamburg | ✔ | dl-de/zero-2-0 | ? | plus bDOM |
| Hessen | ✔ (seit 2022) | dl-de/zero-2-0 | 4–8 /m² | LAS 1.3 |
| Sachsen | ✔ | dl-de/zero-2-0 | 4 /m² | LAZ 1.2, klassifiziert |
| Sachsen-Anhalt | ✔ (seit 2023) | dl-de/zero-2-0 | 3–5 /m² | mit RGB |
| Thüringen | ✔ | dl-de/zero-2-0 | 4 /m² | LAZ 1.4 |
| Baden-Württemberg | gebührenpflichtig (8 /m²), Öffnung angekündigt | — | — | LoD2 + bDOM als Ersatz |
| Niedersachsen | laut Liste gebührenpflichtig, Öffnung 2024 angekündigt — **prüfen** | — | 4 /m² | DOM1-WCS ist offen (Registry) |
| RP, MV, SL, HB | gebührenpflichtig (10–120 €/km²) | — | 2–5 /m² | LoD2 (RP) bzw. DOM-Kacheln als Ersatz |
| Schleswig-Holstein | nur DGM1 offen | — | — | bDOM 2020–2023 |

Neun Länder mit offener Punktwolke decken mit BY, NW, HE, SN, ST, TH, BB, BE, HH
einen großen Teil der Bevölkerung ab; wo sie fehlt, bleibt Stufe A/C/D.

### 6.3 Was das rechnerisch kostet — realistisch, je Garten, einmalig

Gemessen an NRW (die größten Kacheln der Liste):

| Schritt | Aufwand | Anmerkung |
|---|---|---|
| Kachel laden | 60–450 MB, Ø 104 MB → 10–60 s | einmal je Kilometerquadrat, Cache auf dem **Volume** mit LRU (Muster: LoD2-Kachel 161 MB) |
| Dekomprimieren | `laspy` + `lazrs`, ~2–5 Mio. Punkte/s → 2–10 s je Kachel | chunkweise lesen, < 300 MB RAM |
| Auf das 300-m-Fenster klippen | ~9 % der Kachel → ≤ 1 Mio. Punkte | Fenster = Garten + 50 m Rand + Reichweite hoher Bäume |
| Rastern (0,5 m oder 1 m) | 600×600 Zellen, numpy-Binning: DTM (Klasse 2, min), DSM (max), **nDSM**, Gebäudemaske (Klasse 6), Vegetationshöhe (3–5), **Kronenansatz** (5. Perzentil der Vegetationspunkte > 1 m je Zelle) | < 2 s |
| Speichern | 360 k Zellen × int16 × 3–4 Ebenen, deflated ≈ 0,5–1 MB je Ort | wie `terrain_window.heights_cm`, nach Ort geschlüsselt, nie im Image |
| **Gesamt** | **1–2 min je Garten, einmalig, im Hintergrund** | nie im Request-Thread: Prozesspool aus Plan 01 (ST-03), Status „wird vermessen" auf der Seite |

Die Kachel selbst darf nach dem Rastern wieder aus dem Cache fallen; behalten
wird nur das Fenster. Für hundert Gärten sind das ~100 MB auf dem Volume.

**Ehrlich zur Auflösung:** bei 4 Punkten/m² hat eine 0,5-m-Zelle im Mittel
*einen* Punkt — dann ist 1 m das ehrliche Raster; 0,5 m erst ab ~8–10 /m²
(Berlin, neuere NRW-Befliegungen, Hessen). Objekthöhen ±0,3–0,5 m: eine 1,8-m-
Mauer ist sicher, ein 30-cm-Hochbeet liegt im Rauschen. Das steht dann als
`vertical_step_m`/Konfidenz dabei, wie bei jeder Quelle hier.

**Was die Punktwolke dem Schattenmodell zusätzlich schenkt:** den
**Kronenansatz** und die Kronenform je Baum (Plan 03, E5 — heute geschätzt aus
der Höhe), Hecken als Körper statt als gezeichnete Linie, und die Trennung
Gebäude/Vegetation, an der `canopies_in` heute scheitert (Doc 84: „ein Zelt
und ein Baum lesen gleich").

### 6.4 Der eigene Garten: das Telefon als Messgerät (Stufe E)

Für Hochbeet, Zaun, jungen Baum und Nachbars Hecke *hinter* dem Zaun gibt es
keine amtliche Quelle mit 1 m². Realistisch und billig für uns ist eine
**Aufnahme durch den Gärtner**:

- **LiDAR-Telefone/Tablets** (iPhone/iPad Pro, ARKit-Scanner-Apps) liefern ein
  Mesh oder eine Punktwolke, 1–5 cm auf kurze Distanz, 5–20 MB. Upload → auf dem
  Server in Sekunden auf 0,25 m gerastert; Georeferenz über 2–3 vom Nutzer im
  Plan angeklickte Passpunkte (Hausecken). Ein Fenster je Garten, ~1 MB.
- **Photogrammetrie aus Fotos** (COLMAP/OpenSfM) ist *nicht* realistisch
  serverseitig: 100 Fotos sind 10–30 min GPU oder Stunden CPU je Garten. Wenn,
  dann auf dem Gerät (ARCore/ARKit machen das bereits) — wir nehmen nur das Ergebnis.
- **Tippen bleibt.** Höhe und Dachform je Element sind heute editierbar; ein
  „AR-Maßband" (Höhe eines Baums aus Winkel und Abstand) wäre die kleinste Stufe.

Das ist opt-in, per Garten, und lizenzfrei — die Daten gehören dem, der sie
gemacht hat, und liegen auf dem Volume wie sein Garten.

### 6.5 Reihenfolge für die 1-m²-Frage

1. **Stufe B in NRW** (Kachel-URL und Index geprüft, dl-zero): Punktwolke →
   nDSM 0,5 m + Klassifikation + Kronenansatz; Prozesspool; Speicher- und
   Zeitbudget als Test.
2. Stufe B in BY, HE, SN, ST, TH, BB, BE, HH — je ein Adapter für Portal und
   Kachelschema (1 km / 2 km, LAZ 1.2–1.4), gemeinsamer Rasterer.
3. **Stufe C (LoD2)** überall dort, wo B fehlt (Abschnitt 4, Feature 3).
4. **Stufe E** als Feature „Meinen Garten vermessen" (Upload, Passpunkte, Raster).
5. Stufe D (bDOM/DOP20) nur für Umrisse, wenn B und C fehlen.

Stufe A bleibt, was sie ist: der schnelle WCS-Ausschnitt, wo ein Land ihn bietet.
