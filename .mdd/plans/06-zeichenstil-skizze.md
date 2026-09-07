# Plan — Ein Plan, der wie eine Zeichnung aussieht („Skizze")

> Die Referenz: Esris ArcWatch-Artikel *Stylish Landscapes* (April 2020). Er
> stellt **Draft Sketch** vor — einen ArcGIS-Pro-Stil von Warren Davison (GIS-
> Analyst, Stadt Waterloo, Kanada), auf ArcGIS Online veröffentlicht, mit den
> Grafik-Assets seines früheren Stils *Field Notes*. Was den Stil ausmacht,
> sagt der Artikel selbst:
>
> - **Strichstärke variiert, Linien „wackeln"**
> - **tintige Aquarell-Kleckse** („inky watercolor splotches")
> - **Farbe läuft über die Linie** („paint bleed")
> - **skizzierte Überschüsse an den Ecken** (Linien laufen über den Eckpunkt hinaus)
> - **Symbole in drei Detailstufen** je Maßstab: Bäume gewinnen Form, Gebäude
>   bekommen leichte Schraffur und Überschüsse
> - Brunnen-Polygon, Baum als Punkt mit Puffer (= Kronengröße), alles mit der
>   Maus von Hand gezeichnet
>
> **Lizenz:** ein `.stylx` für ArcGIS-Pro-Nutzer unter den Bedingungen des
> ArcGIS-Online-Items; die Zeichnungen sind das Werk des Autors. Nichts davon
> darf oder muss in einen Web-Plan wandern. Die *Qualitäten* sind Techniken,
> keine Werke — und genau die lassen sich mit eigenen Marken nachbauen. Deshalb
> ist der zweite Teil der Frage der wichtigere: **ein austauschbares Grunddesign**,
> damit ein lizenzierter Stil später einhängbar wäre und der eigene sauber bleibt.

---

## 1. Was da ist, und was schon einmal scheiterte

Der Plan ist ein SVG in Gartenmetern: je Kind ein `<pattern>` in Metern
(`GardenSymbols.tsx`: Dachlatten, Stipple, Grashalme, Ripple, Kronenblobs),
ein `feTurbulence`/`feDisplacementMap`-„Wobble"-Filter auf der Objektgruppe,
Blüten als gestreute Punkte (Doc 56), Sonnenkarte und Relief als Ebenen.

**Doc 58 („Pigment, and a rim where the paint stops") ist zurückgenommen.**
Der Nutzer sah den zweiten Versuch und sagte: liest sich immer noch technisch.
Was gelernt wurde und hier nicht neu entdeckt werden darf:

1. Der Wobble war unsichtbar — es braucht **zwei Wellenlängen** (eine biegt die
   Kontur, eine raut sie auf) und genug Auslenkung.
2. „Pigment" als graues Rauschen ist Schmutz — Variation muss in der **Farbe der
   Fläche** liegen.
3. **Das Kachelgitter ist das stärkste technische Signal:** Halme in Reihen,
   Kies im Raster, Latten gleichmäßig. Kacheln müssen 2–3 m groß sein und 40–50
   *von Hand verstreute* Marken tragen; Dächer als versetzte Ziegel statt paralleler
   Linien; Ripples wandern und brechen ab.
4. Die Kontur war ein harter Einheitsstrich — dünner, halbtransparent, die
   Fläche trägt die Form.
5. **Ansehen statt ableiten:** die Browser-Pane liefert bei diesem SVG Blankos;
   erst ein Raster-Harness (`qlmanage`) machte Änderungen beurteilbar.

Und die eigentliche Diagnose aus Doc 58: *jede Fläche war genau eine flache
Farbe* — ein gewackelter Rand um ein perfekt gleichmäßiges Feld ist immer noch
CAD. Der Fehler lag nicht im Filter, sondern in der **Komposition**.

---

## 2. Das austauschbare Grunddesign: Themes

Ein Theme ist ein TypeScript-Modul, das eine Schnittstelle `PlanTheme` erfüllt.
Der Plan (`CanvasScene`, `GardenSymbols`, `ClusterLayer`, `SunMap`) liest
**alles** durch das Theme; kein Pattern-Name, keine Farbe, kein Filter steht
mehr fest im Code.

```
PlanTheme
├─ tokens        Papier (Farbe, Körnung), Tinten, Waschfarben je Kind,
│                Strichstärken, Schattenfarbe — als CSS-Custom-Properties
├─ symbols       je Kind × Detailstufe: <pattern>/<symbol>-Definitionen
├─ filters       Wobble, Bleed, Papierkorn — Filterkette je Ebene
├─ rules         welche Detailstufe bei welchem Maßstab (`spacing`),
│                Überschuss-Länge, Klecksdichte, Schattenrichtung, Beschriftung
└─ modes         light / dark / prefers-contrast / forced-colors
```

Drei Slots: **„Skizze"** (eigen, lizenzrein, Standard), **„Technisch"** (der
heutige Plotter-Look, wird beim Extrahieren zum ersten Theme — ohne sichtbare
Änderung, alle Tests grün), und ein **freier Slot** für einen später lizenzierten
Stil. Auswahl im Kopf-Menü, gemerkt per `localStorage` (pro Betrachter) — nichts
davon ist Katalog- oder Gartendaten.

**Lizenz-Reinraum-Regel** für „Skizze": alle Marken selbst gezeichnet oder
prozedural erzeugt; Schriften unter OFL, lokal gebündelt (keine CDN — Plan 01
CSP); CC0-Quellen erlaubt und in `THIRD_PARTY.md` gelistet; Esris Stylesheet
wird nicht nachgezeichnet. Ein Test verlangt, dass jede Symboldatei einen Kopf
mit Autor und Lizenz trägt.

---

## 3. „Skizze": Element für Element

Jede Qualität aus dem Artikel, übersetzt in eine SVG-Technik — und wo Doc 58
schon eine Antwort hat, dessen Antwort.

| Qualität (Draft Sketch) | Umsetzung in „Skizze" |
|---|---|
| Papier | Warmes Off-White mit leichtem Korn (`feTurbulence`, niedrige Alpha, *multiply*) auf dem Grundrechteck; dunkler Modus: Schiefer mit Kreide-Tinten (Doc 41: nicht invertieren) |
| Linien wackeln, Stärke variiert | Wobble mit **zwei Oktaven** (Doc 58); Konturen **doppelt**: ein dünner Tintenstrich plus ein leicht versetzter, hellerer zweiter Strich — der Skizzen-Doppelstrich; Stärken je Kind aus Tokens |
| Überschüsse an den Ecken | **Geometrie, kein Filter:** jede Kante in `canvas/` um 0,15–0,3 m über den Eckpunkt verlängern (skaliert mit `spacing`, sonst sind es bei 60 m Spanne Dornen). Das eine Merkmal, das jede Handzeichnung verrät |
| Aquarell-Kleckse | 6–8 unregelmäßige Blob-Pfade, prozedural platziert, aus der Element-ID geseedet (wie Doc 56) — gleicher Plan, gleiche Kleckse; niedrige Alpha in der Waschfarbe |
| Paint bleed | `feMorphology dilate` + Weichzeichner *außerhalb* der Kontur, schwach — Farbe, die über den Strich läuft; dazu der Rand-Saum (Doc 58: erode-Differenz) |
| Flächen nicht flach | Farbvariation **im Farbton der Fläche** (Doc 58, Punkt 2), grobe Turbulenz |
| Detailstufen | über `spacing` (Meter je Rasterschritt): **LoD0** (> 60 m Spanne) nur Waschflächen; **LoD1** (20–60 m) Krone als Umriss mit wenigen Lappen, Gebäude mit Umriss; **LoD2** (< 20 m) Krone mit Buchten und inneren Aststrichen und Schlagschatten, Gebäude mit **handgesetzter Schraffur** (versetzt, ungleich — kein Gitter) und Überschüssen |
| Symbole je Kind | Pflaster: ungleiche Platten; Kies: von Hand verstreut; Wasser: wandernde, abbrechende Ripples; Rasen: gestreute Halme; Hecke: gebuchtete Masse; Weg: Doppellinie mit Textur — alle in 2–3-m-Kacheln mit 40–50 Marken (Doc 58, Punkt 3) |
| Schlagschatten der stehenden Dinge | **Der Plan kennt die Sonne.** Der Zeichnungsschatten ist der echte Schatten eines Referenzmoments (z. B. 15. Juni, 15 Uhr) bei niedriger Alpha, kurz gehalten — ein *Zeichnungs*-Schatten, nicht die Schattenkarte, und trotzdem etwas, das kein anderer Plan hat |
| Beschriftung | Handschrift-Anmutung mit OFL-Schrift (z. B. *Patrick Hand*, *Caveat*), **nur** für Element-Labels im Plan; UI-Text bleibt Systemschrift |
| Farbpalette | Gedeckt und erdig: Salbei, Sand, Terrakotta, Schieferblau für Wasser; Tinte warmbraun statt Schwarz; Blütenpunkte behalten ihre **wahre** Farbe (Semantik vor Stil) und werden als kleine Tupfer gemalt |

**Was Lesbarkeit schützt:** Texturen sind Dekoration, Namen tragen Bedeutung
(Doc 41); Sonnenkarte und Blütenpunkte müssen über dem Papier lesbar bleiben
(Kontrast messen); `prefers-contrast: more` und `forced-colors` schalten
automatisch auf „Technisch".

---

## 4. Der Prozess — weil er zweimal die Ursache war

1. **Raster-Harness zuerst.** Ein Skript (`npm run plan:sheet`) rendert die
   echte `CanvasScene` für drei Fixture-Gärten (klein, Hof, Stadt) in drei
   Zoomstufen zu PNG — mit Playwright/Chromium, weil jsdom nicht malt — und legt
   einen Kontaktbogen ab. Jede Stilentscheidung wird *angesehen*, nicht begründet.
2. **Der Nutzer beurteilt den Bogen**, nicht den Code. Abnahme (Doc 58): jemand
   nennt es eine *Zeichnung* eines Gartens, nicht ein Diagramm. Zwei
   Review-Runden sind eingeplant, nicht eine.
3. **Vorher/Nachher-Galerie** im Feature-Doc, damit die dritte Iteration die
   erste nicht wiederholt.
4. **Leistungsbudget:** Filter sind teuer. Eine Filterkette je *Ebene*, nie je
   Element; die interaktive Ebene (Griffe, Auswahl, Cluster) bleibt filterfrei;
   Malzeit bei 100 Elementen messen, auf einem Telefon prüfen;
   `prefers-reduced-motion`/Low-Power reduziert auf LoD1.

---

## 5. Stufen

| Stufe | Inhalt |
|---|---|
| 0 | `PlanTheme`-Schnittstelle; heutiges Aussehen als Theme „Technisch" extrahiert — **keine sichtbare Änderung**, Tests grün, Pattern-IDs nur noch über das Theme |
| 1 | Raster-Harness und Kontaktbogen |
| 2 | „Skizze" LoD0/1: Papier, Waschflächen mit Farbvariation, Wobble in zwei Oktaven, Doppelstrich, Überschüsse |
| 3 | Symbole LoD2: Bäume, Gebäude (Schraffur), Kies/Pflaster/Wasser/Rasen ohne Gitter |
| 4 | Kleckse, Bleed, Saum, Sonnenschatten als Zeichnungsschatten |
| 5 | Beschriftung mit gebündelter OFL-Schrift; Dark Mode; Kontrast-/Forced-Colors-Fallbacks |
| 6 | Theme-Wahl im Kopf-Menü; dritter Slot dokumentiert (Schnittstelle, Lizenzhinweis) |

**Aufwand, grob:** 0 etwa 2 PT; 1 etwa 1 PT; 2 etwa 2–3 PT; 3 etwa 3–4 PT
(Marken zeichnen kostet Zeit); 4 etwa 2 PT; 5 etwa 1–2 PT; 6 etwa 1 PT. Dazu
die Review-Runden. Zusammen etwa drei Wochen.

## 6. Risiken

- **Dritter Versuch am selben Urteil.** Deshalb Harness und Bogen *vor* jeder
  Stilarbeit, und Komposition (Symbole, Überschüsse, Kleckse) vor Filtern.
- **Zu viel Stil frisst Bedeutung.** Sonnenkarte, Blütenfarben und Auswahl sind
  Aussagen; sie dürfen nicht unter Papier verschwinden — Kontrast wird gemessen.
- **SVG-Filter auf Mobilgeräten.** Messen; notfalls LoD1 als Standard auf Touch.
- **Lizenzdisziplin.** Jede Marke hat einen Kopf; keine Nachzeichnung fremder Symbole.
