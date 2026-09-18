import './theme.css';

import type { DecoratedShape, LevelOfDetail, PlanTheme } from '../types';
import { DraftSketchDefs } from './Defs';
import { drawOverlays } from './draw';
import { OVERLAYS } from './generated/rules';
import { IMAGES } from './generated/symbols';

/*
 * Warren Davison's Draft Sketch as a theme of the plan (doc 97), used and
 * adapted with his permission (THIRD_PARTY.md). What his symbols are is
 * generated from his file; which of ours gets which is decided here.
 */

/** His scale ranges, 1:1,500 and 1:2,500, as metres per pixel at 96 dpi. */
const NEAR_UNTIL = 0.4;
const MID_UNTIL = 0.66;

/** Symbols he draws in three levels of detail. */
const LEVELLED: Readonly<Record<string, string>> = {
  building: 'ds-building',
  crown: 'ds-tree',
};

/** Symbols he draws one way. Hedges, walls, fences and unnamed things are his
 *  washes for now; feature 3 draws them properly. His heavy outline round them
 *  was tried and turned a fence into a black bar. */
const FILLS: Readonly<Record<string, string>> = {
  grass: 'ds-grass',
  water: 'ds-water',
  stipple: 'ds-sand',
  slabs: 'ds-brick',
  tarmac: 'ds-grey',
  planting: 'ds-brown',
  foliage: 'ds-green',
  masonry: 'ds-grey',
  fence: 'ds-brown',
  plain: 'ds-grey',
};

function symbolOf(symbol: string, lod: LevelOfDetail): string {
  const levelled = LEVELLED[symbol];
  return levelled === undefined ? (FILLS[symbol] ?? 'ds-grey') : `${levelled}-${lod}`;
}

/** Whose outline a shape is drawn with: the ground is his dashed line and nothing else. */
function outlineOf(shape: DecoratedShape, lod: LevelOfDetail): string {
  return shape.ground ? 'ds-dashed' : symbolOf(shape.symbol, lod);
}

export const draftSketch: PlanTheme = {
  id: 'draft-sketch',
  label: 'Draft Sketch',
  provenance: 'Warren Davison (Draft Sketch)',
  Defs: DraftSketchDefs,
  fill: (symbol, lod) => `url(#${symbolOf(symbol, lod)})`,
  // Beds are painted by the stylesheet, as in Technisch: theme.css hands it his wash.
  bedFill: () => undefined,
  objectsFilter: null,
  lodAt: (metresPerPixel) =>
    metresPerPixel < NEAR_UNTIL ? 'near' : metresPerPixel < MID_UNTIL ? 'mid' : 'far',
  decorate: (shape, lod, metresPerPixel) =>
    drawOverlays(shape, OVERLAYS[outlineOf(shape, lod)] ?? [], metresPerPixel),
  images: IMAGES,
  // As agreed with him (THIRD_PARTY.md), word for word.
  credit: 'Zeichenstil nach Draft Sketch von Warren Davison, verwendet und angepasst mit seiner '
    + 'Erlaubnis · with assistance from Louis Hill (@NKYmapLAB)',
};
