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

Leaves drifting slowly behind the front door, in the palette the plan already
uses.

## Decisions

### CSS transforms, and no animation loop

A `requestAnimationFrame` loop on a landing page runs until the tab is closed.
These are seven composited transforms with no JavaScript running at all, so the
cost is a repaint the compositor was going to do anyway.

Negative delays start each leaf part-way through its journey, so the page does
not open with all seven lined up at the top — and every one has its own
duration, because identical timing reads as a machine rather than as weather.

### Stopped, not slowed

`prefers-reduced-motion: reduce` removes it. Slowing an animation is still an
animation to somebody who asked their system for less motion.

Feature 41 promised this and nothing on the site moved, so the promise had cost
nothing until now. It is guarded by a test rather than by good intentions.

### It is decoration and behaves like it

`aria-hidden`, `pointer-events: none`, behind the content, and at 16% opacity.
A background that competes with the words in front of it is a background that
failed — and the check for that is looking at the page, which is why this
feature's definition of done is not an assertion.

### Only on the front door

Inside a garden the plan is the picture. Leaves drifting over somebody's bed
layout would be decoration arguing with data.

## Definition of done

The landing page moves gently, the words stay the thing you read, and the motion
stops entirely when the system asks for less.
