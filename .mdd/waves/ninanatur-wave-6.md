---
id: ninanatur-wave-6
title: "Wave 6: One plan, fewest possible parcels"
initiative: ninanatur
initiative_version: 2
status: planned
depends_on: ninanatur-wave-5
demo_state: "A finished plan turns into a shopping list split across as few nurseries as possible"
created: 2026-08-27
hash: 6cce2dab
---

# Wave 6 — One plan, fewest possible parcels

## The problem, stated properly

This is not a sorting problem. Minimise

    sum(shipping cost of each nursery used) + sum(item prices)

subject to every needed plant being covered by a nursery that stocks it. That is
a set-cover with fixed costs — a CP-SAT model in OR-Tools, solved in
milliseconds at this size.

The interesting extension: when one plant is stocked only by a nursery used for
nothing else, offer an ecologically equivalent species that an already-used
nursery carries. Near-identical score, one parcel fewer.

## Scope

**In:**
- Nursery adapters over partner feeds (Shopify/WooCommerce product endpoints
  where offered) — by agreement, not by scraping
- Availability and price sync
- The optimisation, with the substitution option
- Order list export

## Constraint

Nursery data is obtained with permission. Nurseries generally want referral
traffic, so an email gets a feed; ten partners with clean data beat a fragile
scraper across a hundred shops. This is the same reasoning that kept the trait
layer on open sources.

## Definition of done

A finished plan produces a shopping list grouped by nursery, with the parcel
count and total cost shown, and substitution suggestions where they save a parcel.
