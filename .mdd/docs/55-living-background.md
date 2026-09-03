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
  - frontend/src/usePrefersReducedMotion.ts
  - frontend/public/meadow.mp4
  - frontend/src/styles.css
routes: []
models: []
test_files:
  - frontend/src/components/LivingBackground.test.tsx
  - tests/test_stylesheet.py
  - tests/test_front_door_video.py
data_flow: greenfield
last_synced: 2026-09-03
status: complete
phase: all
mdd_version: 11
tags: [animation, reduced-motion, landing, decoration, video]
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

### A filmed meadow over the mote field

The user supplied 50 seconds of a wildflower meadow and asked whether it could
replace the background. It could, and it is better than the motes at saying what
this site is for — those are the plants the catalogue is about.

The mote field did not go away. It is what plays when the video must not or
cannot, and there are three such cases:

- **`prefers-reduced-motion`.** The video is not rendered at all, so it is never
  fetched. Hiding it in CSS would still download three megabytes and decode them
  for the one visitor who asked for the opposite. This is why there is now a
  `usePrefersReducedMotion` hook: CSS can only hide, and hiding is not enough.
- **Before the first frame.** The field stays mounted until `playing` fires, so
  a slow connection shows a moving background rather than a black rectangle.
- **A codec this browser will not take.** `onError` puts the field back.
- **`navigator.connection.saveData`.** Three megabytes is nothing on a desk and
  a real amount on a train. Absent — Safari and Firefox have no `connection` —
  is not "saving", and plays.

Once the video is actually playing the field is `display: none` — a set of
animated gradients composited under an opaque video is work done for nobody.

### Three megabytes, not eleven

The source was 1280×720 H.264, 50.05 s, 11.6 MB, no audio track. Re-encoded at
CRF 34 with x264 `veryslow` it is **3.2 MB** and indistinguishable at this size;
540p was tried and rejected, because upscaled it loses the fine grass and the
meadow starts looking waxy.

**It must not be trimmed.** The loop is closed over the full 50 seconds — the
first and last frames differ by 1.36 of 255 on average, 10 at the worst pixel —
and cutting it anywhere would introduce the seam the clip does not have.

Delivery is the FastAPI static mount, which already answers `video/mp4` with
`accept-ranges: bytes` and a 206 to a range request.

### The scrim is why the text is still readable

The clip is a sunlit meadow and the front door's type is pale. The scrim is a
gradient, not a flat wash — darkest at the top where the title and buttons are —
because a uniform 60% black turns a film into a grey rectangle that happens to
move. It is rendered only while the video plays; the mote field was built dark
already.

Two colours moved with it. The stat labels and the panel hints were `#a9c0a0`,
which measured **4.64** against the brightest frame of the clip — over the 4.5
floor by nothing at all. Measured, not guessed: the video was sampled every 2.5
seconds through a canvas, composited with the scrim's alpha at that height, and
the worst case taken. They are now `#c6d8bd` and `#bccfb2`, worst case **6.04**.

### It covers, and it is anchored low

`object-fit: cover` with `object-position: 50% 65%`. A 16:9 clip in a portrait
phone window loses most of its width; anchoring low keeps the flowers on screen
instead of the blurred hedge at the top.
