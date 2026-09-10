---
id: ninanatur-wave-27
title: "Wave 27: One plan, one basket"
initiative: ninanatur
initiative_version: 23
status: planned
depends_on: ninanatur-wave-23
demo_state: "Ein fertiger Plan wird zur Einkaufsliste: je Beet die Arten und Mengen, nach Anbietern und Paketen gebündelt, mit dem Regiosaatgut des eigenen Ursprungsgebiets vorbelegt — und ein Knopf je Anbieter öffnet dessen Warenkorb mit genau diesen Positionen. Was bestellt, geliefert und gepflanzt ist, steht danach im Plan. Eine einzige Kasse für alle Anbieter kommt, sobald drei Gärtnereien angeschlossen sind."
created: 2026-08-27
hash: d6dfe028
---

# Wave 27: One plan, one basket

## Demo-State

Ein fertiger Plan wird zur Einkaufsliste: je Beet die Arten und Mengen, nach
Anbietern und Paketen gebündelt, mit dem Regiosaatgut des eigenen
Ursprungsgebiets vorbelegt — und ein Knopf je Anbieter öffnet dessen Warenkorb
mit genau diesen Positionen. Was bestellt, geliefert und gepflanzt ist, steht
danach im Plan. Eine einzige Kasse für alle Anbieter kommt, sobald drei
Gärtnereien angeschlossen sind.

*(This wave is not complete until this can be manually demonstrated.)*

*This is Wave 25 — "One plan, fewest possible parcels" — moved to 27 and
re-planned on 2026-09-07, when the owner asked how ordering through the site
could actually work. It had moved from Wave 6 to 13 to 20 to 25 before, each
time because the garden itself turned out to be worth more work; this time it
moves because three waves the garden needs (the workspace, the height data,
the light model) go first. Ordering is still the last step of the loop.*

Detailed plan, in German, with the legal checklist and the model comparison:
`.mdd/plans/07-einkaufen-aus-dem-plan.md`. **Not legal advice**; the points
named there are the questions to put to a lawyer before stage 3.

## The problem, stated properly

The optimisation is unchanged from the original plan: minimise

    sum(shipping cost of each nursery used) + sum(item prices)

subject to every needed plant being covered by a nursery that stocks it — a
set cover with fixed costs, a CP-SAT model in OR-Tools, milliseconds at this
size. The extension stands too: when one plant is stocked only by a nursery used
for nothing else, offer an ecologically equivalent species that an already-used
nursery carries — near-identical score, one parcel fewer.

What is new is the *how*. Three models were compared:

| | **M1 List + hand-off** | **M2 Order service** (the owner's proposal) | **M3 Marketplace, split payment** |
|---|---|---|---|
| Who sells to the customer | the shop | us, or the shop through a mandate | the shop; we broker |
| Payment | in each shop | we collect and advance | one checkout at a licensed PSP, split per seller |
| Supervision (ZAG) | none | **critical** — collecting and forwarding third-party money is a money-remittance business unless an exemption applies; the "commercial agent" exemption is narrow and under revision (PSD3) | none, as long as the PSP holds the funds and each seller contracts with it (BaFin guidance) |
| Duties | none | full consumer-law duties if we sell in our own name: 14-day withdrawal, warranty on living plants, packaging registration, plant passports, seed-marketing rules for wild seed | platform duties: DSA Art. 30/31 trader traceability, P2B, PStTG reporting (threshold: under 30 sales *and* under 2 000 € per seller and year), VerpackG § 7 Abs. 7 seller check |
| Automation | Storefront Cart APIs, deep links | none without a shop API; changing delivery addresses on one account trigger fraud checks | order API or e-mail/CSV per seller |
| Customer experience | N checkouts | one | one |

**Decision for the wave:** build M1 now — it delivers the visible value (the
list, the parcels, the regionality) in weeks with no duty at all, and it *is*
the data groundwork M3 needs. M2 is a manual pilot at most, for a dozen orders,
to learn demand; it is not a product. M3 is stage 3, gated on three partners
and a legal review.

## Two things only this project can say

- **The region.** Native wild-plant seed (*Regiosaatgut*) is produced and
  certified for **22 Ursprungsgebiete** (RegioZert, VWW-Regiosaaten; the
  Erhaltungsmischungsverordnung). In the open landscape the origin is mandatory
  (§ 40 BNatSchG); in a private garden it is the right recommendation — and this
  app knows the garden's coordinates, hence its origin region. No shop can say
  "the right seed for *this* place"; this one can.
- **The quantity.** The plan knows every bed's area and every species' space
  (`space_m2`), so it can say how many plants and how many grams, not just which.

Plants add two constraints seed does not have: seasonal shipping windows, and a
**plant passport** for distance sales to consumers — the shipper's duty, and a
reason partners must be nurseries that already ship.

## Constraint, unchanged

Nursery data is obtained with permission. A product feed is a link — the
lingua franca is the Google Merchant feed format, which almost every shop
already produces. Ten partners with clean data beat a fragile scraper across a
hundred shops; the same reasoning that kept the trait layer on open sources,
and the same `CLAUDE.md` rule: `robots.txt` **and** the licence, or nothing.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 0 | who-sells-what | — | planned | — |
| 1 | which-region-this-is | — | planned | — |
| 2 | how-much-of-each | — | planned | 0 |
| 3 | fewest-parcels | — | planned | 2 |
| 4 | hand-it-to-the-shop | — | planned | 3 |
| 5 | what-came-of-it | — | planned | 4 |
| 6 | one-checkout | — | planned | 5 |

Three stages, and the demo-state's first two sentences are stage 2:

- **Stage 1 — the data:** 0, 1, 2.
- **Stage 2 — the list, and the hand-off (M1):** 3, 4.
- **Stage 3 — the loop closed, and one checkout (M3):** 5, 6. Gated: three
  signed partners, a legal entity for commissions, and a lawyer's answer to the
  checklist in the plan.

## What each one is

### 0. who-sells-what

Catalogue-side tables, written with the same `upsert` discipline as everything
here:

| Table | Holds |
|---|---|
| `supplier` | name, legal form, seat, feed URL, order channel (API / e-mail / CSV), shipping profile, plant-passport capability, status |
| `offer` | `taxon_id` ↔ supplier SKU, **form** (seed / potted plant / bulb), pack (pieces, grams, sowing area), price, availability, season window, **origin region** for seed, `retrieved_at`, `source="supplier:<name>"`, `license="feed agreement"` |
| `shipping_profile` | base cost, free-from, parcels per form, lead time, countries |

A Merchant-feed adapter (XML/CSV) per partner; SKU → `taxon_id` through the
existing GBIF chain (`ingest/names.py`); cultivars (`'Alba'`) are not catalogue
species and are attached to their species, visibly marked. Feeds are fetched
through `ingest/http.py` and refreshed on a schedule, never scraped.

### 1. which-region-this-is

The 22 origin regions as polygons — the BfN/VWW map, licence to be checked;
otherwise traced from an open source — a garden assigned by point-in-polygon,
and regional seed **preferred by default** for that region, with the reason
stated. Decided with the owner: supra-regional seed only on request.

### 2. how-much-of-each

Quantities from area: plants per m² by growth form and `space_m2`, seed in
g/m² from the supplier's sowing rate, both editable by the gardener. The
shopping list in the inspector (Wave 23), per bed, form switchable between seed
and plant where both are offered.

### 3. fewest-parcels

The original wave: CP-SAT set cover with fixed costs, the substitution rule
scored with the fit and insect models, parcel count and total cost shown, and
the reason for every substitution said in words.

### 4. hand-it-to-the-shop

Per supplier a button that opens **their** cart with exactly these lines:
Shopify's Storefront Cart API (`cartCreate` → the shop's `checkoutUrl`; the old
Checkout API was retired on 2025-04-01), Shopware's Store API, WooCommerce
add-to-cart URLs, product deep links otherwise. No money, no contract, no
reporting. The customer pays N times — that is the price of M1, and the page
says so plainly rather than pretending a single checkout.

Tests: a cart hand-off per adapter against recorded fixtures; the list never
contains a line without an offer; a supplier with no feed cannot be handed to.

### 5. what-came-of-it

Order status back into the plan — *bestellt → geliefert → gepflanzt* — so the
planting becomes a fact rather than a plan, and the bloom calendar reads what
is actually in the ground. Needs an account: the share token is not enough to
hold an address and an order history (Wave 20).

### 6. one-checkout

M3: the nurseries as connected seller accounts at a payment provider (Stripe
Connect, Mangopay, Lemonway, Adyen for Platforms, Mollie Connect — KYC by the
PSP), one checkout, the PSP splits per seller, each seller ships its parcel, a
commission for the platform. **The money never touches us** and each seller
contracts with the PSP — the construction that needs no ZAG licence. Contracts
are between customer and nursery; the platform says so unmistakably. Seller
notification by order API where a shop has one, by structured e-mail otherwise.

With it the platform duties named in the plan: DSA trader traceability, P2B
terms, PStTG registration and reporting, VerpackG seller checks, per-seller
withdrawal instructions, price display, data protection for the address handed
to each seller. Not built before the legal review has answered.

## Open — must be settled in this wave

- **Which nurseries, on what terms.** Candidates to approach (to be checked):
  Rieger-Hofmann and Saaten Zeller (Regiosaatgut), Naturgarten-Shop, wild
  perennial nurseries such as Hof Berg-Garten, Gärtnerei Strickler,
  Staudengärtnerei Gaißmayer, Wildstaudengärtnerei Wiesenknopf, seed houses such
  as Blauetikett-Bornträger or Syringa, the Naturgarten e. V. partner list.
  **Three are enough to start.** What we offer: qualified, species-level,
  regional demand and no fee before the first sale; what we need: a feed link,
  a shipping profile, season windows, an order channel, a signed agreement.
- **The legal entity and VAT treatment** for commissions — a precondition for
  stage 3, not a detail.
- **The commission model.**
- **Whether M2 is piloted at all.** The learning is real, so is the friction.

## Deliberately not in this wave

- Scraping any shop, or any product data without an agreement.
- Selling in NinaNatur's own name as a product. The order-service model is a
  pilot at most.
- Non-commercial-licensed data of any kind in the offers.
- Warehousing, logistics, or anything physical — the nurseries ship.
