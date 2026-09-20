import type { JSX, ReactNode } from 'react';

import type { Point } from '../canvas/viewport';

/**
 * How near the plan is looked at. A theme may draw a tree as a dot far away
 * and as a crown close up; Technisch draws everything one way.
 */
export type LevelOfDetail = 'near' | 'mid' | 'far';

/** A shape as a theme's decorations see it (doc 97). */
export interface DecoratedShape {
  /** Unique on the plan and stable: the key of what is drawn for it, and part of its ids. */
  key: string;
  /** What `kinds.ts` draws it as; `planting` for a bed. */
  symbol: string;
  /** The garden's own ground, which is paper rather than a thing on it. */
  ground: boolean;
  /** Its outline, in garden metres with y north. */
  points: Point[];
  /** What it is, as `kinds.ts` names it: `bed` for a bed (doc 98). */
  kind: string;
  /** Its own line, for an element drawn as one — a fence, a wall, a hedge. */
  line: Point[] | null;
  /** How far a raised bed stands above the ground; 0 for everything else. */
  raised: number;
  /** The lines that draw its roof, as the server's roof model gives them. */
  roofLines: [Point, Point][];
  /** Its roof's shape, as stored: a pent's one line is its upper edge. */
  roof: string;
  /** How wide the band round a line is, in metres, as the element carries it —
   *  null for anything that is not drawn along a line. Measuring it from the
   *  outline works for a straight way and not for one that bends: there the
   *  outline's width across is the bend's own reach. */
  bandWidth: number | null;
  /** Where this thing's shadow falls at the drawing's moment, in garden metres
   *  (doc 99), or null where the model says it casts none. A theme draws its
   *  drop shadow there instead of wherever its style put one. */
  shadow: Point | null;
}

/** What a theme draws for the plan as a whole rather than for one shape: a
 *  street network's outline, which no single street can draw (doc 98). */
export interface PlanProps {
  shapes: readonly DecoratedShape[];
  metresPerPixel: number;
}

/** What the plan's furniture — north, scale, title — is drawn from (doc 98). */
export interface FurnitureProps {
  metresPerPixel: number;
  /** The garden's name. */
  title: string;
  /** When the garden last changed, as the server says it. */
  updatedAt: string | null;
}

/** What a theme draws for a shape besides its fill: under all the shapes, and over them. */
export interface Decoration {
  under: ReactNode;
  over: ReactNode;
}

/**
 * The plan's look, in one place (doc 96).
 *
 * Until Wave 24 it was decided in four: the symbol patterns, a fill attribute
 * in the scene, a filter in the stylesheet and the stylesheet's tokens. A theme
 * holds the first three, and scopes the fourth: `plan-theme--{id}` is the class
 * its token overrides hang off. What a kind *is* (`kinds.ts`) and what the plan
 * *says* — the sun map, selection, focus — are not a theme's to change.
 */
export interface PlanTheme {
  /** Stable: the picker remembers it, and it names the theme's token scope. */
  id: string;
  /** What the picker calls it. */
  label: string;
  /** Whose marks these are, in the words the provenance rule allows. */
  provenance: string;
  /** Every pattern and filter the plan's layers refer to by id, drawn once in its defs. */
  Defs: () => JSX.Element;
  /** The paint for an element that `kinds.ts` draws as `symbol`, at this level
   *  of detail — `url(#…)`, or undefined to leave it to the stylesheet. Its
   *  `kind` too, for a theme that draws kinds of one symbol apart (doc 98). */
  fill: (symbol: string, lod: LevelOfDetail, kind?: string) => string | undefined;
  /** The paint for a bed. Its own member, because a bed is the one shape whose
   *  look is part of what it says: selected, raised, planted. */
  bedFill: (lod: LevelOfDetail) => string | undefined;
  /** The one filter over the shapes, as `url(#…)`, or null. Nothing else is
   *  filtered: a displaced hit target is a target somewhere it is not drawn. */
  objectsFilter: string | null;
  /** What the plan is drawn on, as a fill — a paper texture under everything
   *  (doc 99). Left out where the page's own background is the paper. */
  paper?: string | undefined;
  /** How much detail to draw: the scale in metres per screen pixel, and — for
   *  a mark that belongs to one shape — how wide that shape is, in metres. A
   *  theme may give a house more than a shrub on the same plan (doc 99).
   *  Without a size it answers for the plan as a whole. */
  lodAt: (metresPerPixel: number, acrossM?: number) => LevelOfDetail;
  /** What is drawn along a shape rather than inside it — ink, shadows, corner
   *  and centre marks (doc 97) — or nothing, when the theme has no such marks.
   *  Never a target: the shape itself stays the only thing a pointer can hit. */
  decorate?: (shape: DecoratedShape, lod: LevelOfDetail, metresPerPixel: number) => Decoration;
  /** Every image its defs draw with, so it can be loaded before the plan is
   *  drawn in it rather than seen arriving piece by piece. */
  images?: readonly string[];
  /** The line its author is credited with, shown beneath the plan whenever it
   *  is drawn in it; none for a theme of our own. */
  credit?: string;
  /** A north arrow, a scale bar and a title block in the theme's hand, in the
   *  plan's corner (doc 98); without it the plan says "N ↑", as it always has. */
  Furniture?: (props: FurnitureProps) => JSX.Element;
  /** What the theme draws for the plan as a whole, under its shapes' own ink. */
  Plan?: (props: PlanProps) => JSX.Element | null;
}
