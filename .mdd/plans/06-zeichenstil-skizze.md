# Plan — Zeichenstil „Draft Sketch": mit Erlaubnis übernommen, in seiner Handschrift erweitert

> **Stand 2026-09-10.** Warren Davison hat schriftlich erlaubt, seinen Stil
> *Draft Sketch* zu verwenden und anzupassen. Das ändert den Plan vom
> 2026-09-07 an der Wurzel: kein lizenzreiner Nachbau der *Qualitäten* mehr,
> sondern **seine Marken als Basis**, maschinell aus dem `.stylx` nach SVG
> geholt, und alles, was ein Gartenplan braucht und der Stil nicht hat —
> Blüten, Laub- und Nadelbäume, Sträucher, Hecken, Dächer nach Dachform,
> Hochbeete — **in seiner Handschrift ergänzt**. Das austauschbare Grunddesign
> bleibt, aus einem anderen Grund als vorher: nicht mehr als Lizenz-Rückfall,
> sondern weil ein Theme, das man wechseln kann, eines ist, das man auch
> verbessern kann.
>
> Was noch gilt: die Lehren aus Doc 58 (zwei gescheiterte Versuche), das
> Raster-Harness vor jeder Stilarbeit, die Review-Runden, das Leistungsbudget,
> die Lesbarkeitsregeln. Was wegfällt: der Reinraum. An seine Stelle tritt eine
> **Herkunftsregel** — jede Marke sagt, ob sie seine ist, angepasst oder unsere.

---

## 1. Die Erlaubnis: was sie abdecken muss, und wo sie liegt

Die Erlaubnis ist ein Rechtsdokument und wird wie eines behandelt:

- **Aufbewahrung außerhalb des öffentlichen Repos** (wie der Sicherheitsplan),
  z. B. beim Owner; im Repo steht `THIRD_PARTY.md` mit Datum, Umfang in einem
  Satz und der vereinbarten Namensnennung.
- **Das Repo trägt keine LICENSE** (geprüft 2026-09-10): öffentlich, aber
  „alle Rechte vorbehalten". Davisons Assets liegen deshalb unter einem eigenen
  Hinweis — *verwendet und angepasst mit Erlaubnis von Warren Davison; nicht
  für Dritte lizenziert* — damit ein Clone des Repos keine Rechte an ihnen
  überträgt, die er nicht hat.
- **Zu bestätigen, falls die Erlaubnis es nicht ausdrücklich sagt** (eine
  E-Mail genügt, sie kommt zur Aufbewahrung dazu):
  1. Veröffentlichung der Assets und unserer Ableitungen im **öffentlichen**
     Repository (Sichtbarkeit ≠ Lizenz, aber es ist Verbreitung);
  2. **kommerzielle** Nutzung — Wave 27 (Einkauf) macht NinaNatur zu einem
     Produkt mit Umsatz;
  3. **Erweiterungen** in seinem Stil unter denselben Bedingungen;
  4. ob die **Field-Notes-Assets** (derselbe Grafik-Fundus, laut seinem
     Artikel) eingeschlossen sind;
  5. seine gewünschte **Credit-Zeile** (Seite, `THIRD_PARTY.md`, ggf. Impressum);
  6. **Widerruf**: was gilt, falls er die Erlaubnis zurücknimmt — dann greift
     Theme „Technisch", und genau dafür bleibt der Schalter.
- **Anstand:** ihm das Ergebnis zeigen, bevor es live geht (Stufe 6).

---

## 2. Was wir bekommen, und in welcher Form

Aus dem ArcWatch-Artikel (April 2020) und der Item-Seite: *Draft Sketch* ist ein
ArcGIS-Pro-Stil (`.stylx`), von der ArcGIS-Online-Item-Seite herunterladbar, mit
Punkt-, Linien- und Flächensymbolen in **drei Detailstufen** — Bäume als Punkt
(Kronengröße über einen Puffer-Effekt) und als Fläche, Gebäude mit Schraffur und
Überschüssen an den Ecken, ein Brunnen-Polygon, Kleckse, Farbbleed, wackelnde
Linien mit variabler Stärke. Der Stylesheet-Ausdruck im Artikel zeigt alle
Elemente.

**Das Format ist gutmütig.** Ein `.stylx` ist eine **SQLite-Datei**: Tabelle
`ITEMS`, je Symbol eine Zeile, die Definition als **CIM-JSON** in der Spalte
`CONTENT`. Lesbar mit `sqlite3` und `json` aus der Standardbibliothek; ein
MIT-lizenziertes Werkzeug (Notebook + Geoprocessing-Tool, nur Stdlib) exportiert
bereits **Punkt-/Marker-Symbole** nach SVG — Vektormarker als `<path>`,
Bildmarker (Base64-PNG) als Bilddateien, y-Achse gespiegelt (CIM y-oben, SVG
y-unten). Linien, Flächen und Effekte deckt es nicht ab; das ist unser Teil
(Abschnitt 3).

**Was wir zusätzlich erbitten:** die **Quell-Assets** (SVG/AI/PNG in voller
Auflösung, die Field-Notes-Marken). Aus dem `.stylx` lässt sich alles holen, aber
gescannte Tuschezeichnungen sind dort als PNG in Symbolgröße eingebettet; für
eine Zeichnung, die in der Nahansicht standhält, sind die Originale besser.

---

## 3. Der Konverter: `.stylx` → Theme

`scripts/stylx_to_theme.py`, nur Standardbibliothek plus Pillow, erzeugt
deterministisch `frontend/src/themes/draft-sketch/` — `tokens.css`,
`symbols.svg` (ein `<defs>`-Block), `rules.ts` (Detailstufen, Größen) — und wird
mit dem Quell-`.stylx` unter `assets/draft-sketch/` eingecheckt. Ein Test
regeneriert und vergleicht: das Theme ist eine Ableitung, keine Handarbeit.

| CIM-Ebene | Nach SVG | Anmerkung |
|---|---|---|
| `CIMVectorMarker` (Ringe, Pfade, Kurven) | `<symbol>` mit `<path d>`; C/Q/A-Kurven 1:1; y-Spiegelung als eine Gruppentransformation | vom MIT-Werkzeug abgedeckt |
| `CIMPictureMarker` / `CIMPictureFill` (Base64-PNG) | `<image href="data:…">` bzw. `<pattern>` mit `<image>`, Kachel in **Metern** (`patternUnits="userSpaceOnUse"`, Doc 41) | Auflösung 2× behalten; Gesamtgröße messen — ab ein paar hundert KB als Sprite-Sheet |
| `CIMSolidFill`, `CIMSolidStroke` | `fill`/`stroke`, Alpha 0–100 → 0–1, Farben → **Tokens** (seine Palette wird die des Themes; Dark Mode nach Doc 41 abgeleitet, nicht invertiert) | |
| `CIMHatchFill` (Winkel, Abstand, Liniensymbol) | `<pattern>` mit dem Liniensymbol, gedreht | Gebäudeschraffur |
| Geometrische Effekte `Wave`, `Jog`, `Offset`, `Dashes` | **Geometrie in `canvas/`**, vorgerechnet mit seinen Parametern (Amplitude, Periode, Wellenform) — nicht als Filter, damit Hit-Ziele und Handles stimmen; `Dashes` als `stroke-dasharray` | die Überschüsse an den Ecken kommen genauso: Kanten um seine Länge verlängert |
| `Buffer`-Effekt (Baum-Punkt → Krone) | unser Kronenradius (`canopy_of`, editierbar) | Datenbasis statt Symbolparameter |
| `CIMCharacterMarker` (Schriftzeichen als Marke) | Glyph-Umriss als `<path>` (fontTools) — **nur wenn die Schrift frei ist**; sonst nachgezeichnet | Schriftlizenz prüfen (Abschnitt 6) |
| Maßstabsbereiche der drei Detailstufen | unsere **LoD-Leiter** über `spacing` (Meter je Rasterschritt) | Punkte (1/72 Zoll) bei Referenzmaßstab → Meter: eine Regel je Symbol, am Kontaktbogen justiert |

**Was verloren geht, benannt:** ArcGIS' Beschriftungsplatzierung (wir haben
eigene Labels), „random"-Wellenformen (emuliert mit festem Seed), und alles, was
nur bei einem Druckmaßstab stimmt — deshalb die LoD-Leiter am Bildschirm statt
seiner Maßstabsbereiche.

---

## 4. Was der Stil nicht hat — und in seiner Handschrift bekommt

Ein Gartenplan braucht mehr, als eine Stadtkarte zeichnet. Die Erweiterungen,
je an die Daten gebunden, die der Plan ohnehin hat:

| Bedarf | Datenbasis | Zeichnung in seiner Hand |
|---|---|---|
| **Blüten** in zehn Farben, drei Größen | `bloom/palette.py`, Farbpunkte (Doc 56), Sekundärfarbe aus Plan 08 | gemalte Tupfer statt Kreise; grau außerhalb der Blütezeit (Regel bleibt) |
| **Laubbaum vs. Nadelbaum**, Krone nach Größe, drei LoDs | `deciduousness`, `growth_form`, `canopy_of` | zwei Kronenfamilien (gebuchtet / gezackt), im Winter-Tagesverlauf kahle Laubkrone |
| **Sträucher** | `growth_form` shrub/subshrub | kleinere, dichtere Kronen |
| **Hecken** | kind `hedge`, Band | geschnittene Masse mit Schraffur an der Schattenseite |
| **Häuser nach Dachform** | `roof` (gable/hip/flat/pent/mix), `roofshape` (Firstrichtung, Traufe) | First als Linie entlang der langen Achse, Walm mit Gratlinien, Flachdach als Fläche, Pult mit einer Traufkante — die Zeichnung sagt, was das Modell weiß |
| Schuppen, Mauern, Zäune | kinds | Latten, Mauerwerk, Pfosten, wie heute, in seiner Strichführung |
| **Hochbeete** | `height_above_ground` > 0 | doppelte Umrisslinie mit Schattenkante |
| Gartengrenze | kind `garden` | gestrichelte Skizzenlinie |
| Rasen, Kies, Pflaster, Wege, Straßen, Teich | kinds | seine Flächen, wo vorhanden; sonst neu, mit den Doc-58-Regeln (2–3-m-Kacheln, 40–50 Marken, kein Gitter) |
| **Kompassrose, Maßstabsbalken, Titelblock** (Gartenname, Datum, Maßstab) | `GardenOut` | eine Zeichnung hat sie; heute steht nur „N ↑" |
| Standpunkt, Sichtlinien | Wave 9 | in derselben Tinte |
| Sonnenkarte, Tagesverlauf | Doc 65 | zwei flache Tinten bleiben (Lesbarkeit); der **Zeichnungsschatten** der stehenden Dinge kommt vom echten Sonnenstand eines Referenzmoments (15. Juni, 15 Uhr), kurz und blass |

**Handschrift heißt Handwerk:** gleiches Medium wie seine Assets (sind sie
gescannte Tusche, werden die Erweiterungen mit Tusche gezeichnet und gescannt;
sind sie Vektor, mit demselben Strichsatz), gleiches Papier, gleiche Tinte,
gleiche Wackelparameter. Jede neue Marke trägt einen Kopf: *Autor NinaNatur,
im Stil von Draft Sketch (W. Davison), Datum*. Seine eigenen Marken tragen
seinen Namen. Das ist die Herkunftsregel, und ein Test prüft, dass keine
Symboldatei ohne Kopf ist.

---

## 5. Theme-Architektur — unverändert, mit anderer Besetzung

```
PlanTheme
├─ tokens    Papier, Tinten, Waschfarben je Kind, Strichstärken, Schattenfarbe
├─ symbols   je Kind × Detailstufe: <symbol>/<pattern>
├─ filters   Papierkorn, Bleed — nur wo SVG einen Effekt nicht als Geometrie kann
├─ rules     LoD-Leiter, Überschusslänge, Klecksdichte, Schattenmoment, Label-Stil
└─ modes     light / dark / prefers-contrast / forced-colors
```

Drei Slots: **„Draft Sketch"** (NinaNatur-Fassung, Standard), **„Technisch"**
(der heutige Plan, als erstes Theme extrahiert, ohne sichtbare Änderung —
und der Rückfall, falls die Erlaubnis je endet), ein freier dritter. Auswahl im
Kopf-Menü, per Betrachter gemerkt.

---

## 6. Prozess, Lesbarkeit, Leistung

- **Erst sehen.** `npm run plan:sheet`: die echte `CanvasScene` für drei
  Fixture-Gärten in drei Zoomstufen als PNG-Kontaktbogen (Playwright/Chromium);
  die Browser-Pane liefert bei diesem SVG Blankos (Doc 58, erneut geprüft).
  Jede Entscheidung am Bogen, nicht am Code; Vorher/Nachher-Galerie im Doc.
- **Zwei Review-Runden mit dem Owner** (nach Stufe 2 und nach Stufe 4) und eine
  Anstandsrunde mit Davison vor dem Ausrollen.
- **Schrift:** welche Schrift seine Textsymbole nutzen, ist zu prüfen; frei
  (OFL) → bündeln; sonst eine OFL-Handschrift (*Patrick Hand*, *Caveat*) — nur
  für Labels im Plan, UI-Text bleibt Systemschrift. Keine CDN (CSP, Plan 01).
- **Lesbarkeit vor Schönheit** (Doc 41): Namen tragen Bedeutung, Texturen sind
  Dekoration; Kontrast von Labels, Sonnenkarte und Blütentupfern über Papier
  wird gemessen; `prefers-contrast: more` und `forced-colors` schalten auf
  „Technisch".
- **Leistung:** Bildmarken als Data-URIs sind Bytes im Bundle — messen, ab
  einigen hundert KB Sprite-Sheet; eine Filterkette je Ebene, nie je Element;
  interaktive Ebene filterfrei; Malzeit bei 100 Elementen auf einem Telefon;
  `prefers-reduced-motion`/Low-Power auf LoD 1.

---

## 7. Stufen und Aufwand

| Stufe | Inhalt | PT |
|---|---|---|
| 0 | `PlanTheme`-Schnittstelle; „Technisch" extrahiert, keine sichtbare Änderung; Herkunfts-Test | 2 |
| 1 | Raster-Harness und Kontaktbogen | 1 |
| 2 | **Konverter** `.stylx` → Theme; Draft Sketch so weit wie vorhanden (Gebäude, Bäume, Flächen, Linien); `THIRD_PARTY.md`, Hinweisdatei, Credit auf der Seite | 2–3 |
| 3 | **Erweiterungen** (Abschnitt 4): Blüten, Laub/Nadel, Sträucher, Hecken, Dachformen, Hochbeete, Kompass/Maßstab/Titelblock | 3–4 |
| 4 | Papier, Bleed, Zeichnungsschatten vom echten Sonnenstand, LoD-Leiter justiert | 1,5 |
| 5 | Schrift, Dark Mode, Kontrast-/Forced-Colors-Rückfälle | 1–2 |
| 6 | Theme-Schalter, Anstandsrunde mit Davison, Ausrollen | 1 |

Etwa **zwölf Personentage** plus Review-Runden — weniger Zeichenarbeit als der
Plan vom 2026-09-07, weil die Basis fertig ist, und mehr Konverterarbeit.

## 8. Risiken

- **Rasterassets in der Nahansicht.** Gescannte Marken werden unscharf; die
  LoD-Leiter zeigt sie nur dort, wo sie scharf sind, und Schlüsselmarken werden
  in Vektor nachgezeichnet — in seiner Hand.
- **Einheiten.** CIM misst in Punkten bei Druckmaßstab; der Plan in Metern am
  Bildschirm. Die Regel je Symbol wird am Bogen gesetzt, nicht gerechnet.
- **Effekte ohne SVG-Gegenstück.** Emuliert als Geometrie; was nicht überzeugt,
  fällt weg, statt halb zu gelingen (Doc 58).
- **Umfang der Erlaubnis.** Abschnitt 1 ist Vorbedingung von Stufe 2, nicht
  Nacharbeit.
- **Zu viel Stil.** Sonnenkarte, Blütenfarben und Auswahl bleiben Aussagen;
  Kontrast wird gemessen.

## 9. Entscheidungen

1. Name und Credit-Zeile des Themes (mit Davison abstimmen).
2. Quell-Assets erbitten (empfohlen) oder nur aus dem `.stylx` arbeiten.
3. Ob die Erweiterungen ihm zur Ansicht gehen, bevor sie live sind (empfohlen).
