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
