# Plan — Einkaufen aus dem Plan heraus (ein vereintes Einkaufserlebnis)

> Die Frage hat zwei Hälften: **wie** bestellt jemand seinen fertigen Plan an
> einem Ort, obwohl Saatgut und Pflanzen auf mehrere spezialisierte Anbieter
> verteilt sind — und **welches Modell** dahinter steht. Der Vorschlag
> „wir bestellen über ein Firmenkonto mit wechselnder Lieferadresse" ist ein
> Bestellservice; er funktioniert als Pilot, ist aber rechtlich und operativ
> die schwächste Form. Die aktuelle Form ist ein **Marktplatz mit geteilter
> Zahlung** (die Gärtnereien als angeschlossene Verkäufer, ein Checkout, N
> Pakete) — und der billige Einstieg davor eine **konsolidierte Einkaufsliste
> mit Übergabe in die Warenkörbe der Partner**. Der Plan empfiehlt, in dieser
> Reihenfolge zu bauen.
>
> Wave 27 (`.mdd/waves/ninanatur-wave-27.md`) hat die Optimierung — Mengen-
> überdeckung mit Fixkosten, so wenige Pakete wie möglich — und die Regel
> „Partnerdaten per Vereinbarung, nie per Scraping" schon gesetzt. Dieser Plan
> baut darauf, er ersetzt es nicht.
>
> **Kein Rechtsrat.** Die rechtlichen Punkte unten sind benannt, damit sie in
> einer Beratung *gefragt* werden; sie sind kein Ersatz dafür.

---

## 1. Ausgangslage — was der Katalog dafür hat und was fehlt

- **Hat:** Arten mit Standortwerten, Insektenwert, Blühkalender, ein Garten mit
  Beeten, Flächen (m²) und Koordinaten. **Nicht:** Lieferanten, Angebote, Preise,
  Verfügbarkeit, Packungsgrößen, Versandprofile, Saisonfenster, Herkunftsregionen.
- **Saatgut ist besonders.** Gebietsheimisches Wildpflanzen-Saatgut
  („Regiosaatgut") wird nach **22 Ursprungsgebieten** produziert und zertifiziert
  (RegioZert, VWW-Regiosaaten; Erhaltungsmischungsverordnung). In der freien
  Landschaft ist die Herkunft Pflicht (§ 40 BNatSchG); im Privatgarten nicht —
  aber es ist die fachlich richtige Empfehlung, und **NinaNatur kennt die
  Koordinaten des Gartens**, also das Ursprungsgebiet. Das ist ein
  Alleinstellungsmerkmal: „das richtige Saatgut für *diese* Region" kann kein
  Shop allein sagen. Anbieter: Rieger-Hofmann (Shop mit Kleinpackungen), Saaten
  Zeller (eher B2B), Naturgarten-Shop, dazu Wildstaudengärtnereien (Kandidaten
  in 7).
- **Pflanzen sind saisonal** (Versandfenster Frühjahr/Herbst), brauchen beim
  Fernabsatz an Endkunden einen **Pflanzenpass** (Pflicht des Versenders), und
  Versandkosten dominieren kleine Bestellungen — deshalb zählt „wenige Pakete".

---

## 2. Die Modelle im Vergleich

| | **M1 Liste + Übergabe** | **M2 Bestellservice** (Vorschlag) | **M3 Marktplatz, geteilte Zahlung** |
|---|---|---|---|
| Wer verkauft dem Kunden? | der Shop | wir *oder* der Shop, je nach Ausgestaltung | der Shop; wir vermitteln |
| Zahlung | im Shop | wir kassieren und verauslagen | ein Checkout beim Zahlungsdienstleister, Aufteilung je Verkäufer |
| Verträge/AGB | keine eigenen Kaufverträge | volle Verbraucherrechtspflichten (bei Eigenhandel) oder Vollmachtskonstrukt | Plattform-AGB, Vermittlerrolle, Pflichten als Online-Plattform |
| Aufsicht (ZAG) | keine | **kritisch**: Einziehen und Weiterleiten fremder Gelder ist Finanztransfer­geschäft, es sei denn, eine Ausnahme greift | keine, solange der lizenzierte PSP die Gelder hält und jeder Verkäufer selbst mit ihm kontrahiert (BaFin-Merkblatt ZAG) |
| Automatisierung | Deep Links / Cart-APIs | keine ohne Shop-API; Adressen wechseln → Betrugsprüfungen der Shops | Bestell-API oder E-Mail/CSV je Verkäufer |
| Nutzererlebnis | N Kassen | eine Kasse | eine Kasse |
| Aufwand | Wochen | Handarbeit je Bestellung | Monate + Partner |
| Einnahmen | Affiliate/Partnerpauschale | Marge | Provision |

### M1 — Konsolidierte Einkaufsliste mit Übergabe

Der Plan wird zur Liste: je Beet die Arten und Mengen (Pflanzen aus dem
Flächenbedarf `space_m2`, Saatgut in g/m²), der Optimierer aus Wave 27 gruppiert
sie nach Anbietern und Paketen; je Anbieter ein Knopf „Warenkorb bei X öffnen".
Wo der Partner **Shopify** nutzt: die *Storefront Cart API* (`cartCreate` → die
`checkoutUrl` des Shops; die alte Checkout-API ist seit 2025-04-01 abgeschaltet).
**Shopware**: Store API (Warenkorb + Checkout headless). **WooCommerce**:
Add-to-Cart-URLs. Sonst Produkt-Deep-Links. Kein Geld, kein Kaufvertrag, keine
Meldepflicht. Der Kunde zahlt N-mal — das ist der Preis, und er ist ehrlich gesagt.

### M2 — Bestellservice mit Firmenkonto

Zwei Rechtsformen, beide mit Haken:

- **Stellvertretung** (wir bestellen *im Namen* des Kunden): braucht eine
  Vollmacht in den AGB, der Shop muss Fremdbestellungen akzeptieren, Rechnung und
  Widerruf laufen zwischen Kunde und Shop — und wenn wir das Geld vorab vom
  Kunden einziehen und an den Shop weiterleiten, sind wir im
  Finanztransfergeschäft (ZAG). Die „Handelsvertreterausnahme" ist eng und unter
  PSD3/PSR in Überarbeitung. Ohne Vorkasse verauslagen wir — Kreditrisiko.
- **Eigenhandel/Kommission** (wir kaufen und verkaufen weiter): wir sind
  Verkäufer — Fernabsatz, 14 Tage Widerruf, Gewährleistung *für lebende
  Pflanzen*, Impressum/AGB, Umsatzsteuer, Verpackungsgesetz (LUCID-Registrierung
  des Vertreibers), Pflanzenpass-Pflichten liegen dann bei uns, und wer
  Wildpflanzen-Saatgut im eigenen Namen vertreibt, muss die Saatgutverkehrs­regeln
  (ErMiV) selbst einhalten.

Operativ: wechselnde Lieferadressen auf einem Firmenkonto lösen Betrugsprüfungen
aus, Bestellungen sind Handarbeit, Rücksendungen chaotisch. **Urteil:** als
manueller Pilot für ein Dutzend Bestellungen brauchbar, um Nachfrage zu lernen —
nicht als Ziel.

### M3 — Marktplatz mit geteilter Zahlung (die heutige Form)

NinaNatur ist die Plattform; jede Gärtnerei ein **angeschlossenes Verkäuferkonto**
beim Zahlungsdienstleister (Stripe Connect, Mangopay, Lemonway, Adyen for
Platforms, Mollie Connect). Der Kunde bezahlt einmal; der PSP teilt je Verkäufer;
jeder Verkäufer versendet sein Paket; wir nehmen eine Provision. **Die Gelder
berühren uns nie**, jeder Verkäufer kontrahiert mit dem PSP — das ist die
Konstruktion, die keine ZAG-Erlaubnis braucht (BaFin-Merkblatt; die Plattform
darf den Zahlungsfluss nicht steuern). Die Kaufverträge entstehen zwischen Kunde
und Gärtnerei; wir sind Vermittler und müssen es unmissverständlich sagen.

Pflichten als Plattform (für die Beratung, nicht abschließend):
- **Digital Services Act** Art. 30/31: Verkäuferidentität prüfen und
  Rückverfolgbarkeit; wer als Verkäufer *erscheint*, haftet wie einer (Art. 6 Abs. 3).
- **P2B-Verordnung**: transparente Bedingungen gegenüber den Händlern.
- **Plattformen-Steuertransparenzgesetz** (seit 2023): Meldung der Verkäufer ans
  BZSt, außer unter 30 Verkäufen *und* unter 2 000 € je Verkäufer und Jahr.
- **Verpackungsgesetz § 7 Abs. 7**: Marktplätze müssen die LUCID-Registrierung
  ihrer Händler prüfen.
- Widerrufsbelehrung je Verkäufer, Button-Lösung, Preisangaben, Datenschutz
  (Adressweitergabe an die Gärtnereien als eigene Verantwortliche; AVV mit dem PSP).

---

## 3. Empfehlung: in dieser Reihenfolge

1. **M1 jetzt.** Es liefert den sichtbaren Nutzen (die Liste, die Pakete, die
   Regionalität) in Wochen, ohne eine einzige Pflicht — und es ist der Datenaufbau,
   den M3 ohnehin braucht (Angebote, Versandprofile, Saisonfenster).
2. **M2 optional als Pilot** mit einem Partner und einem Dutzend Bestellungen,
   nur um Nachfrage und Reibung zu messen — nicht ausbauen.
3. **M3, sobald drei Partner zusagen.** Provision statt Marge, kein Geld in
   eigenen Händen, eine Kasse.

---

## 4. Datenmodell (Katalogseite, per `upsert`-Disziplin wie alles hier)

| Tabelle | Inhalt |
|---|---|
| `supplier` | Name, Rechtsform, Sitz, Feed-URL, Bestellkanal (API / E-Mail / CSV), Versandprofil-ID, Pflanzenpass-Fähigkeit, Status |
| `offer` | `taxon_id` ↔ Lieferanten-SKU, **Form** (Saatgut / Topfpflanze / Zwiebel), Packung (Stück, g, Aussaatfläche), Preis, Verfügbarkeit, Saisonfenster, **Ursprungsgebiet** (Saatgut), `retrieved_at`, `source="supplier:<name>"`, `license="feed agreement"` |
| `shipping_profile` | Grundkosten, versandkostenfrei ab, Pakete je Form, Lieferzeit, Länder |
| `origin_region` | die 22 Ursprungsgebiete als Polygone (BfN/VWW — Lizenz **prüfen**, sonst aus einer offenen Quelle nachzeichnen); Zuordnung eines Gartens per Punkt-in-Polygon |
| `order`, `order_line` (nur M3) | Bestellung je Verkäufer, Status (bestellt / versendet / geliefert / **gepflanzt**) |

**Feeds statt Scraping.** Die Lingua franca ist das *Google-Merchant-Feed*-Format
(XML/CSV) — fast jeder Shop erzeugt es schon; die Bitte an den Partner ist ein
Link. Namensauflösung SKU → `taxon_id` über die vorhandene GBIF-Kette
(`ingest/names.py`); Sorten (`'Alba'`) sind keine Katalog-Arten und werden als
Cultivar der Art zugeordnet, sichtbar markiert.

---

## 5. Der Ablauf im Produkt

1. **Plan → Liste.** „Einkaufsliste" im Inspektor (Plan 05): je Beet Arten und
   Mengen, Form wählbar (Saatgut/Pflanze), Regionalhinweis („dein Garten liegt in
   Ursprungsgebiet 4 — Westdeutsches Berg- und Hügelland").
2. **Optimieren** (Wave 27): wenigste Pakete, Ersatzvorschlag „ökologisch
   gleichwertig, aber vom schon genutzten Anbieter" über Fit und Insektenwert.
3. **Übergabe (M1)** je Anbieter — oder **Kasse (M3)** mit Adresse (Konto nötig:
   das Share-Token reicht dafür nicht, siehe Plan 01), Zahlung beim PSP,
   Aufteilung, Bestätigung je Verkäufer.
4. **Status zurück in den Plan:** „bestellt → geliefert → gepflanzt" schließt
   den Kreis mit dem Blühkalender — die Pflanzung wird zur Tatsache statt zum Plan.

---

## 6. Partnerstrategie

**Wen ansprechen (Kandidaten, zu prüfen):** Rieger-Hofmann und Saaten Zeller
(Regiosaatgut), Naturgarten-Shop, Wildstaudengärtnereien wie Hof Berg-Garten,
Gärtnerei Strickler, Staudengärtnerei Gaißmayer, Wildstaudengärtnerei Wiesenknopf,
Saatgut-Versender wie Blauetikett-Bornträger oder Syringa; die Partnergärtnereien
des Naturgarten e. V. als Liste. **Drei genügen für den Start.**

**Was wir bieten:** qualifizierte Nachfrage auf Artniveau und mit Region,
keine Gebühr vor dem ersten Verkauf, eine Feed-Spezifikation von einer Seite.
**Was wir brauchen:** Feed-Link, Versandprofil, Saisonfenster, Bestellkanal,
eine unterschriebene Partnervereinbarung (für M3: Anschluss beim PSP).

---

## 7. Stufen und Aufwand

| Stufe | Inhalt | Aufwand |
|---|---|---|
| P0 | Entscheidung Rechtsform/Modell; erste Partnergespräche; Rechtsberatung zu M3-Pflichten | Kalenderwochen, wenig Code |
| P1 | **M1**: `supplier`/`offer`/`shipping_profile`, Feed-Adapter (Merchant-Feed), Ursprungsgebiete, Einkaufsliste im Inspektor, Übergabe je Shop | 5–8 PT |
| P2 | **Optimierer** (Wave 27, CP-SAT), Ersatzvorschläge | 3–5 PT |
| P3 | **M3**: PSP-Anbindung (Connect), Kasse, Aufteilung, Verkäufer-Benachrichtigung, Rechtstexte, Meldeprozesse | 10–15 PT + Beratung |
| P4 | Statusrückfluss, Saisonfenster-Logik („bestellbar ab März"), Nachbestellung | 3 PT |

## 8. Entscheidungen für den Owner

1. **Rechtsträger und Umsatzsteuer** für Provisionen (M3) — Voraussetzung, kein
   Detail.
2. **Provisionsmodell** (Prozent, Pauschale, oder Partnerpauschale bei M1).
3. **Ob M2 überhaupt pilotiert wird** — der Lerngewinn ist real, die Reibung auch.
4. **Regionalität als Standard:** Regiosaatgut des eigenen Ursprungsgebiets
   vorbelegen, überregionales nur auf Wunsch? Empfehlung: ja, und sagen warum.
