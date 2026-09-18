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
   *  of detail — `url(#…)`, or undefined to leave it to the stylesheet. */
  fill: (symbol: string, lod: LevelOfDetail) => string | undefined;
  /** The paint for a bed. Its own member, because a bed is the one shape whose
   *  look is part of what it says: selected, raised, planted. */
  bedFill: (lod: LevelOfDetail) => string | undefined;
  /** The one filter over the shapes, as `url(#…)`, or null. Nothing else is
   *  filtered: a displaced hit target is a target somewhere it is not drawn. */
  objectsFilter: string | null;
  /** Which level of detail a scale gets, in metres per screen pixel. */
  lodAt: (metresPerPixel: number) => LevelOfDetail;
  /** What is drawn along a shape rather than inside it — ink, shadows, corner
   *  and centre marks (doc 97) — or nothing, when the theme has no such marks.
   *  Never a target: the shape itself stays the only thing a pointer can hit. */
  decorate?: (shape: DecoratedShape, lod: LevelOfDetail, metresPerPixel: number) => Decoration;
  /** Every image its defs draw with, so it can be loaded before the plan is
   *  drawn in it rather than seen arriving piece by piece. */
  images?: readonly string[];
  /** The line its author is credited with, shown on the plan whenever it is
   *  drawn in it; none for a theme of our own. */
  credit?: string;
}
