import './theme.css';

import type { DecoratedShape, Decoration, LevelOfDetail, PlanTheme } from '../types';
import { DraftSketchDefs } from './Defs';
import { drawOverlays } from './draw';
import { drawAlong } from './drawAlong';
import { OVERLAYS } from './generated/rules';
import { IMAGES } from './generated/symbols';
import { DraftSketchFurniture } from './ours/Furniture';
import { DraftSketchRoads } from './ours/Roads';
import { HEDGE, RAISED, ROOF } from './ours/rules';
import type { LineOverlay, Overlay } from './overlays';

/*
 * Warren Davison's Draft Sketch as a theme of the plan (docs 97, 98), used and
 * adapted with his permission (THIRD_PARTY.md). What his symbols are is
 * generated from his file; which of ours gets which is decided here.
 */

/** His scale ranges, 1:1,500 and 1:2,500, as metres per pixel at 96 dpi: what
 *  the plan as a whole is drawn at, where nothing says how big the thing is. */
const NEAR_UNTIL = 0.4;
const MID_UNTIL = 0.66;

/** What one shape gets, by how wide it is drawn (doc 99). His richest crown is
 *  three rings and a scatter of splotches, which needs about fifty pixels to
 *  land; at a dozen nothing but the outline survives. Measured on the contact
 *  sheet: at 40 m the houses are 89 pixels across and the shrubs 13. */
const NEAR_FROM_PX = 48;
const MID_FROM_PX = 14;

/** Symbols he draws in three levels of detail. */
const LEVELLED: Readonly<Record<string, string>> = {
  building: 'ds-building',
  crown: 'ds-tree',
};

/** Kinds that share a symbol with another but get his own: a shrub is his Tree 2. */
const BY_KIND: Readonly<Record<string, string>> = {
  shrub: 'ds-shrub',
};

/** Symbols he draws one way. Hedges and unnamed things are his washes; fences
 *  and walls carry his line symbols over theirs (doc 98). His heavy outline
 *  round them was tried and turned a fence into a black bar. */
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

/** His line symbols, laid along the elements of these kinds. */
const ALONG: Readonly<Record<string, string>> = {
  fence: 'ds-wood-fence',
  wall: 'ds-brick-wall',
};

function symbolOf(symbol: string, lod: LevelOfDetail, kind?: string): string {
  const own = kind === undefined ? undefined : BY_KIND[kind];
  if (own !== undefined) return `${own}-${lod}`;
  const levelled = LEVELLED[symbol];
  return levelled === undefined ? (FILLS[symbol] ?? 'ds-grey') : `${levelled}-${lod}`;
}

/** Whose outline a shape is drawn with, and what ours adds to it. A fence's
 *  line is its whole drawing; the ground is his dashed line and nothing else. */
function overlaysOf(shape: DecoratedShape, lod: LevelOfDetail): Overlay[] {
  if (shape.ground) return [...(OVERLAYS['ds-dashed'] ?? [])];
  if (shape.kind === 'fence') return [];
  // A street's outline belongs to the network, not to the one way (ours/Roads).
  if (shape.kind === 'street') return [];
  return [
    ...(shape.raised > 0 ? RAISED : []),
    ...(OVERLAYS[symbolOf(shape.symbol, lod, shape.kind)] ?? []),
    ...(shape.roofLines.length > 0 ? ROOF : []),
    ...(shape.kind === 'hedge' ? HEDGE : []),
  ];
}

function decorate(shape: DecoratedShape, lod: LevelOfDetail, metresPerPixel: number): Decoration {
  const round = drawOverlays(shape, overlaysOf(shape, lod), metresPerPixel);
  const symbol = ALONG[shape.kind];
  if (symbol === undefined) return round;
  const along = drawAlong(shape, (OVERLAYS[symbol] ?? []) as readonly LineOverlay[],
    metresPerPixel, shape.kind === 'wall');
  return { under: round.under, over: [round.over, along.over] };
}

export const draftSketch: PlanTheme = {
  id: 'draft-sketch',
  label: 'Draft Sketch',
  provenance: 'Warren Davison (Draft Sketch)',
  Defs: DraftSketchDefs,
  fill: (symbol, lod, kind) => `url(#${symbolOf(symbol, lod, kind)})`,
  // Beds are painted by the stylesheet, as in Technisch: theme.css hands it his wash.
  bedFill: () => undefined,
  objectsFilter: null,
  lodAt: (metresPerPixel, acrossM) => {
    if (acrossM === undefined) {
      return metresPerPixel < NEAR_UNTIL ? 'near' : metresPerPixel < MID_UNTIL ? 'mid' : 'far';
    }
    const across = acrossM / metresPerPixel;
    return across >= NEAR_FROM_PX ? 'near' : across >= MID_FROM_PX ? 'mid' : 'far';
  },
  decorate,
  images: IMAGES,
  Furniture: DraftSketchFurniture,
  Plan: DraftSketchRoads,
  // As agreed with him (THIRD_PARTY.md), word for word.
  credit: 'Zeichenstil nach Draft Sketch von Warren Davison, verwendet und angepasst mit seiner '
    + 'Erlaubnis · with assistance from Louis Hill (@NKYmapLAB)',
};
