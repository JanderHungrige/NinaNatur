# Plan — Die Plan-Seite als Arbeitsplatz, nicht als Bildlaufseite

> Die Beschwerde: „man muss viel hoch und runter scrollen." Sie ist berechtigt,
> und sie ist messbar. Gemessen am 2026-09-07 im gebauten Bundle
> (`ninanatur/web/dist`) am Garten *Schattencheck* (7 Elemente, 3 Beete), per
> DOM-Messung, weil die Browser-Pane den SVG-Plan nicht abbildet:
>
> | Situation | Dokumenthöhe | Bildschirme | Bemerkung |
> |---|---|---|---|
> | Desktop 1280×720, Tab „Zeichnen" | 1 835 px | **2,5** | linke Spalte 1 638 px, rechte 606 px |
> | Mobil 375×812, Tab „Zeichnen" | 2 683 px | 3,3 | der Plan beginnt bei **1 945 px** — 2,4 Bildschirme tief |
> | Mobil 375×812, Tab „Säen", ein Beet gewählt | **8 747 px** | **10,8** | das Panel „Vorschläge" allein **6 725 px** |
>
> Und ein Befund, der kein Layout ist, sondern ein Fehler: der Plan selbst war
> in der Messung **27 px hoch** (Desktop) bzw. 12 px (Mobil) — siehe B1.

---

## 1. Warum die Seite scrollt: die Struktur

Zwei Spalten (`.layout`, 22rem + Rest, ab 72rem eine Spalte), die linke Spalte
trägt **zwei Tabs mit zusammen elf Panels**, die rechte den Plan und drei
Panels:

| Links · Zeichnen | Links · Säen | Rechts |
|---|---|---|
| Garten-ID (68 px) | Vorhandene Bepflanzung (407) | Steuerleiste + Plan |
| Tabs (88) | Filter (227) + Filterzeile (44) | Jahr abspielen (58) |
| Zeichnen-Werkzeuge (254) | Artinfo (bei Bedarf) | Blühjahr (220) |
| **Boden im Garten (448)** | **Vorschläge (6 725)** | Insektenwert (160) |
| Konto zuordnen, Sichtlinien | | Elementmenü (Popover) |
| Beete-Liste (297) | | |
| Baumvorschläge | | |
| Sonne und Schatten | | |
| Gezeichnete Objekte (363) | | |

Drei Dinge folgen daraus:

1. **Die Kernschleife spannt sich über beide Tabs und beide Spalten.** Beet
   auswählen (links, Zeichnen) → Tab wechseln → Vorschlag wählen (links, Säen,
   in einer 6 700-px-Liste) → auf den Plan schauen (rechts, oben) → weiter.
   Ab Zeile drei der Liste ist der Plan aus dem Bild; jedes „Pflanzen" heißt
   drei Bildschirme hochscrollen, um zu sehen, was passiert ist.
2. **Die rechte Spalte ist meist leer, die linke zu voll.** Bei einem frischen
   Garten zeigt rechts zwei „Noch nichts gepflanzt"-Kästen unter dem Plan, links
   stapeln sich 1 600 px Formulare. Das breite Feld wird nicht genutzt.
3. **Einmalfragen stehen dauerhaft da.** „Boden im Garten" ist eine Frage pro
   Garten (Doc 48) und bleibt als 448-px-Formular für immer in der Sidebar.

Auf dem Telefon kommt hinzu: eine Spalte, der Plan zuunterst. Wer auf dem Handy
plant, sieht Werkzeug und Plan nie zugleich.

---

## 2. Befunde, die vor dem Umbau behoben gehören

### B1 — Der Plan kollabiert: Selbstbezug zwischen viewBox und Höhe · **Fehler**

`useViewport` misst das SVG-Element selbst (`getBoundingClientRect`) und
schreibt Breite/Höhe ins `view`; `viewBox(view)` leitet daraus das
Seitenverhältnis der viewBox ab; und weil `.canvas { height: auto }` ist,
bestimmt die viewBox wiederum die *gerenderte* Höhe des SVG. Ein Kreis: eine
einmal zu kleine Messung (Tab im Hintergrund, kurzes Fenster, mobile
Adressleiste, Tastatur eingeblendet) friert als Seitenverhältnis ein und erholt
sich nie — beobachtet: viewBox `-20 -0.6 40 1.2`, Plan 12 px hoch, bis zum Reload.

**Fix:** die Höhe des Plans darf nie aus dem Plan selbst kommen. Die Bühne
(`.canvas-stage`) bekommt eine eigene Höhe (`height: min(75vh, 0.75 × Breite)`
oder `aspect-ratio`), das SVG füllt sie (`width:100%; height:100%`), gemessen
wird die Bühne. Ein vitest für `viewBox()`: aus einer Messung mit Höhe 0 darf nie
ein Seitenverhältnis < 0,3 entstehen. Manuell: Garten in einem 200 px hohen
Fenster öffnen, dann maximieren — der Plan muss mitwachsen.

### B2 — Der Statustext steht am Seitenende · **UX**

`.status` (`role="status"`) sitzt unter allem. Beim Scrollen in der Liste ist
„Gepflanzt" unsichtbar; nur Screenreader hören es. Fix: als Toast am
Viewport-Rand, `aria-live` bleibt.

### B3 — Die Vorschlagsliste rendert alles · **Performance**

28 Zeilen zu je ~240 px, plus Gehölze, jede mit zwei Buttons — bei 50 Zeilen
sind das mehrere hundert DOM-Knoten pro Neuladen. Zusammen mit dem
Lade-Wasserfall aus Plan 01 (O2) ist das der Grund, warum „Pflanzen" träge wirkt.

---

## 3. Das Ziel: ein Editor-Layout

Kein Framework-Wechsel, kein Neuschreiben — React und CSS bleiben. Das Muster
ist das jedes Zeichenwerkzeugs (Figma, QGIS, Canva): **der Plan füllt den
Bildschirm, alles andere docken an ihm an und scrollen in sich.**

```
┌───────────────────────────────────────────────────────────────┐
│ Kopf: Marke · Gartenname/ID · ↶ ↷ · Sonne/Schatten · Konto   │  sticky, 56 px
├────┬──────────────────────────────────────────┬───────────────┤
│ W  │                                          │ Inspektor     │
│ e  │              PLAN                        │ (kontext-     │
│ r  │        füllt 100dvh − Kopf − Leiste      │  abhängig,    │
│ k  │        Pan/Zoom im Element               │  scrollt in   │
│ z  │                                          │  sich, 360–   │
│ e  │                                          │  420 px,      │
│ u  │                                          │  ziehbar)     │
│ g  │                                          │               │
├────┴──────────────────────────────────────────┴───────────────┤
│ Leiste: Blühjahr-Monate · ▶ Jahr · Tagesverlauf · Legende      │  einklappbar
└───────────────────────────────────────────────────────────────┘
```

### 3.1 Die vier Zonen

- **Kopf (sticky):** Marke, Gartenname mit ID-Ausklapper (heute ein 68-px-Panel),
  Undo/Redo, der Schatten-Schalter als Toggle, Rückmeldung, Konto. Die
  Versionsmarke bleibt.
- **Werkzeugleiste (links, 56 px, vertikal):** Auswahl, Rechteck, Kreis, Dreieck,
  Vieleck, Freihand, Stempel (die Palette der Kinds als Ausklappmenü),
  Standpunkt. Tooltips mit Tastenkürzel; `role="toolbar"`, Pfeiltasten. Das
  ersetzt „Zeichnen" (254 px) und die Stempelpalette.
- **Plan (Mitte):** die volle Höhe. Zoom-Knöpfe und Rastermaß als kleine
  Overlay-Leiste in einer Ecke (heute eine eigene Zeile über dem Plan). Die
  Sonnenkarte und der Tagesverlauf sind Ebenen *auf* dem Plan, geschaltet im Kopf.
- **Inspektor (rechts):** zeigt, was zur **aktuellen Auswahl** gehört —
  - *nichts gewählt:* der Garten: Boden (eine Zeile + „ändern"), Licht-Zusammen­fassung,
    Blühjahr-Miniatur, Insektenwert, Baumvorschläge als Karte, Liste der Elemente;
  - *ein Beet gewählt:* dessen Werte, was darin steht, **die Vorschläge** — mit
    Filtern als Chips in einem klebrigen Kopf *im Panel*, die Liste virtualisiert
    und in sich scrollend; „Pflanzen" hebt den neuen Cluster im Plan hervor;
  - *ein Hindernis gewählt:* das Elementmenü (existiert als Popover; wird
    Inspektor-Inhalt);
  - *eine Pflanze gewählt:* die Artinfo mit Farbnotiz.
  Der Inspektor ist ein `<aside aria-label="Details">` und hat einen eigenen
  Scrollbereich. Die Auswahl bleibt, was sie ist: **eine** Quelle der Wahrheit
  (Doc 52), nur dass sie jetzt auch entscheidet, was rechts steht.
- **Leiste (unten, einklappbar):** Blühjahr als Monatsstreifen, „Jahr abspielen",
  Tagesverlauf-Regler, die Farblegende der Sonnenkarte. Alles, was *Zeit* ist,
  liegt an einem Ort, und der Plan darüber reagiert darauf.

### 3.2 Was verschwindet oder sich zurückzieht

- **Die zwei Tabs.** Zeichnen und Säen sind keine getrennten Tätigkeiten,
  sondern zwei Enden derselben Schleife; der Inspektor macht die Trennung überflüssig.
- **„Boden im Garten" als Dauerformular.** Wird Teil eines **Einstiegs mit drei
  Schritten** beim ersten Öffnen (Boden · Schatten berechnen · erstes Beet), danach
  eine Zeile im Garten-Inspektor.
- **Zwei leere „Noch nichts gepflanzt"-Kästen.** Werden eine Zeile mit einem
  Pfeil auf den nächsten Schritt.
- **Sichtlinien, Baumvorschläge, „Konto zuordnen":** kontextuell — Sichtlinien
  als Werkzeug, Baumvorschläge als Markierung im Plan (*„3 gefundene Bäume"*) mit
  Karte im Inspektor, Konto zuordnen im Kopf-Menü.

### 3.3 Mobil

Der Plan ist Vollbild; der Inspektor wird ein **Bottom Sheet** mit drei
Rastpunkten (25 / 60 / 90 %); die Werkzeugleiste eine untere Leiste; die
Zeitleiste ein Streifen über dem Sheet-Griff. `touch-action: none` auf dem Plan
gibt es schon; das Sheet braucht Fokusfalle und Escape.

### 3.4 Was gleich bleibt

Jede Interaktion ist tastaturbedienbar (die Docs 49/51/52 haben das teuer
erkämpft); `prefers-reduced-motion`, Kontrast, Dark Mode; die Fachlogik der
Komponenten (`BedPlantings`, `SuggestionList`, `ShadeSwitch`, `ElementMenu`,
`BloomTimeline`, `InsectScore`) wird **umgehängt, nicht neu geschrieben**.

---

## 4. Umsetzung in Stufen

Doc → Test → Code, Branch je Stufe nach `dev-deployment`, **im echten Browser
angesehen** — die Pane kann diesen SVG nicht abbilden (Doc 58 hat dieselbe
Lehre gezogen). `App.tsx` hat 1 455 Zeilen; die Regel sagt 300. Der Umbau ist
die Gelegenheit, nicht ein zweites Problem.

| Stufe | Inhalt | Nutzen sofort |
|---|---|---|
| 0 | **B1 beheben** (Bühnenhöhe), B2 (Toast) | der Plan verschwindet nicht mehr |
| 1 | **Schnellgewinn:** die rechte Spalte `position: sticky; top: <Kopf>` — der Plan bleibt beim Scrollen der Liste im Bild. ~20 Zeilen CSS | die Beschwerde ist zu 70 % adressiert |
| 2 | **App-Shell:** `GardenWorkspace` (Layout), `ToolRail`, `Inspector` (Kontext-Router über die Auswahl), `TimelineDock`; `App.tsx` auf Zustand und Effekte reduziert (`useGarden`-Hook) | Editor-Layout, Tabs weg |
| 3 | Einstieg mit drei Schritten; Boden/Konto/Sichtlinien/Bäume kontextuell | Sidebar-Ballast weg |
| 4 | **Vorschlagsliste** virtualisiert, kompakte Zeilen (Name · Farbpunkt · Blühmonate als Streifen · Fit-Badge · „+"), Chips-Filter, Hervorhebung im Plan nach „Pflanzen" | die 6 700 px werden ein Fenster |
| 5 | Mobil: Bottom Sheet, untere Werkzeugleiste | Handy wird benutzbar |
| 6 | Feinschliff: Tokens (Abstände, Typo-Skala, ein Panel-Stil), Tastenkürzel-Hilfe (`?`), Leerzustände | Wirkt „modern", weil konsistent |

**Aufwand, grob:** 0–1 einen Tag; 2 etwa 4–5 PT; 3 etwa 2 PT; 4 etwa 3 PT;
5 etwa 3 PT; 6 etwa 2 PT. Stufe 1 lohnt sich, noch bevor 2 beginnt.

---

## 5. Abnahme — messbar, nicht geschmacklich

- Die Kernschleife (Beet wählen → Art wählen → Pflanze im Plan sehen) braucht
  bei 1280×720 **und** bei 375×812 **keinen Seiten-Scroll**. Scroll gibt es nur
  *in* Panels.
- Die Dokumenthöhe des Arbeitsplatzes ist die Viewporthöhe (`documentHeight ≤
  innerHeight + 1`).
- Der Plan ist nie kleiner als 40 % der Viewporthöhe, und seine Höhe hängt
  nicht von seiner eigenen Messung ab (B1-Test).
- Ein Playwright-Rauchtest (`create-e2e`-Skill liegt bereit) misst genau diese
  drei Zahlen an einem Fixture-Garten mit 50 Vorschlägen — der Regressionstest
  für die Beschwerde selbst. jsdom kann Layout nicht; die vitest-Tests sichern
  Struktur und Tastatur (Landmarken, eine Auswahlquelle, Fokusfluss im Sheet).
- Ein Mensch öffnet den Garten auf dem Telefon und pflanzt drei Arten, ohne den
  Plan aus dem Auge zu verlieren.

## 6. Entscheidungen

1. Tabs abschaffen (empfohlen) oder als Inspektor-Reiter behalten?
2. Inspektor rechts (Lesefluss Plan → Details) oder links (Werkzeuge nah an
   der Hand)? Empfehlung: Werkzeuge links, Details rechts, wie in jedem Editor.
3. Einstieg mit drei Schritten als Overlay oder als leerer Inspektor mit
   Aufforderungen? Empfehlung: Inspektor — kein Modal vor dem ersten Blick.
