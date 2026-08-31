---
id: 55-living-background
title: A Page That Breathes
edition: MDD
initiative: ninanatur
wave: ninanatur-wave-13
wave_status: complete
depends_on: []
relates: [41-garden-style]
source_files:
  - frontend/src/components/LivingBackground.tsx
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/components/LivingBackground.test.tsx
  - tests/test_stylesheet.py
data_flow: greenfield
last_synced: 2026-08-31
status: complete
phase: all
mdd_version: 11
tags: [animation, reduced-motion, landing, decoration]
path: Landing/Background
integration_contracts:
  - from: 41-garden-style
    function: prefers-reduced-motion is respected
    when: anything on the site moves
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# A page that breathes

## What this is

A field of motes rising slowly out of a lit floor, in green and gold, behind the
title and the figures. The first version was seven drifting leaves; the user
asked for something more imposing and gave a reference picture.

## Decisions

### The whole front door, edge to edge

This went in two steps. It began as a dark hero band with daylight below —
chosen over darkening everything, on the grounds that the forms and the map had
no business being dark. Seeing it, the user asked for the whole page,
borderless.

They were right, and the first answer was the timid one. A dark band with a
white page under it is a banner; the field only reads as a place once it runs
past the edges of what it is behind. The panels became glass over the field
rather than paper on top of it, which is what let the rest of the page go dark
without becoming unreadable.

**The garden view stays on paper.** The dark ground is scoped to
`.app--front-door`, which is set only while no garden is open. A plan is a
drawing to be read closely; the front door is a photograph.

### Three layers, not three hundred nodes

Each layer holds its entire field as repeated radial gradients in one background
image. The browser composites three layers and animates one transform on each.

A node per particle would be a composited layer per particle; a canvas would be
a `requestAnimationFrame` loop running until the tab is closed. This is neither,
and it is dense enough to look like the reference.

Each layer's height is a whole number of tiles and each travels exactly half of
it, so the loop is seamless without anybody matching numbers to the viewport.
The three speeds are the depth: faint motes drift far away while brighter ones
climb past them.

### A floor to rise from

Without the bright band along the bottom the motes merely exist. With it they
are coming from somewhere, which is what the reference picture is doing and what
"aufsteigend" actually asks for.

### Stopped, not slowed — and not hidden

`prefers-reduced-motion: reduce` sets `animation: none`. Slowing an animation is
still an animation to somebody who asked their system for less motion.

**What changed from the first version:** it used to be `display: none`, which was
right when the background was seven leaves over white and wrong now that the
field is the hero's ground — hiding it would leave an empty dark box. The
promise was never "no background"; it was "no motion", and the guard test asserts
that instead.

### It is decoration and behaves like it

`aria-hidden`, `pointer-events: none`, behind the content. A background that
competes with the words in front of it is a background that failed — and the
check for that is looking at the page, which is why this feature's definition of
done is not an assertion. It took four passes of looking: too sparse, then a floor
nobody could see, then a hero band that turned out to be a banner.

### Only on the front door

Inside a garden the plan is the picture. A particle field over somebody's bed
layout would be decoration arguing with data.

## Definition of done

The hero moves the way the reference picture does, the words stay the thing you
read, and the motion stops entirely when the system asks for less.
