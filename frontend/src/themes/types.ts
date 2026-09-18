import type { JSX } from 'react';

/**
 * How near the plan is looked at. A theme may draw a tree as a dot far away
 * and as a crown close up; Technisch draws everything one way.
 */
export type LevelOfDetail = 'near' | 'mid' | 'far';

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
}
