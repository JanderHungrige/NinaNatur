import { describe, expect, it } from 'vitest';

import {
  DEFAULT_ROOM_M2,
  MAX_DOTS,
  clustersFor,
  defaultCentre,
  keepInside,
  radiusFor,
} from './clusters';
import { covers } from './geometry';

const SQUARE = [[0, 0], [6, 0], [6, 4], [0, 4]];
const L_SHAPE = [
  { x: 0, y: 0 }, { x: 6, y: 0 }, { x: 6, y: 2 },
  { x: 2, y: 2 }, { x: 2, y: 6 }, { x: 0, y: 6 },
];

function planting(overrides: Record<string, unknown> = {}) {
  return {
    planting_id: 1,
    taxon_id: 7,
    canonical_name: 'Salvia pratensis',
    raw_name: null,
    quantity: 5,
    x: null,
    y: null,
    ...overrides,
  } as Parameters<typeof clustersFor>[1][number];
}

function colour(overrides: Record<string, unknown> = {}) {
  return {
    planting_id: 1,
    colour: 'violet',
    months: [5, 6, 7],
    space_m2: null,
    ...overrides,
  } as Parameters<typeof clustersFor>[2][number];
}

describe('radiusFor', () => {
  it('grows with the number of plants', () => {
    expect(radiusFor(20, 0.5)).toBeGreaterThan(radiusFor(5, 0.5));
  });

  it('grows with the room one plant claims', () => {
    expect(radiusFor(5, 4)).toBeGreaterThan(radiusFor(5, 0.2));
  });

  it('falls back when the catalogue says nothing', () => {
    // The ordinary case, not the exception: the catalogue records no spread at
    // all, and the height it estimates from is known for 44% of species.
    expect(radiusFor(9, null)).toBeCloseTo(Math.sqrt((DEFAULT_ROOM_M2 * 9) / Math.PI), 5);
  });

  it('never draws a single plant as a speck', () => {
    expect(radiusFor(1, 0.001)).toBeGreaterThanOrEqual(0.22);
  });
});

describe('defaultCentre', () => {
  it('puts an unplaced cluster inside the bed', () => {
    expect(covers(L_SHAPE, defaultCentre(3, L_SHAPE))).toBe(true);
  });

  it('is not in the notch of an L', () => {
    // A bounding-box guess would put flowers in the part that is not the bed.
    for (let id = 1; id < 40; id += 1) {
      expect(covers(L_SHAPE, defaultCentre(id, L_SHAPE))).toBe(true);
    }
  });

  it('puts the same planting in the same place every time', () => {
    // A patch that wanders between reloads reads as the garden twitching.
    expect(defaultCentre(12, L_SHAPE)).toEqual(defaultCentre(12, L_SHAPE));
  });

  it('puts different plantings in different places', () => {
    expect(defaultCentre(1, L_SHAPE)).not.toEqual(defaultCentre(2, L_SHAPE));
  });
});

describe('clustersFor', () => {
  it('draws one cluster per planting, in flower or not', () => {
    // The whole point of replacing the colour band: an empty bed and a bed full
    // of leaves used to look the same.
    const clusters = clustersFor(
      SQUARE,
      [planting(), planting({ planting_id: 2, canonical_name: 'Achillea millefolium' })],
      [colour(), colour({ planting_id: 2 })],
      1,
    );

    expect(clusters).toHaveLength(2);
    expect(clusters.every((c) => c.dots.length > 0)).toBe(true);
    expect(clusters.every((c) => c.colour === null)).toBe(true);
  });

  it('colours a cluster in the months it flowers', () => {
    const [inJune] = clustersFor(SQUARE, [planting()], [colour()], 6);
    const [inJanuary] = clustersFor(SQUARE, [planting()], [colour()], 1);

    expect(inJune!.colour).toBe('violet');
    expect(inJanuary!.colour).toBeNull();
  });

  it('is grey when no month is being played', () => {
    const [cluster] = clustersFor(SQUARE, [planting()], [colour()], null);
    expect(cluster!.colour).toBeNull();
  });

  it('honours a position the gardener set', () => {
    const [cluster] = clustersFor(
      SQUARE, [planting({ x: 1.5, y: 2.5 })], [colour()], 6,
    );
    expect(cluster!.centre).toEqual({ x: 1.5, y: 2.5 });
  });

  it('draws a plant the catalogue cannot name, grey and unnamed by it', () => {
    const [cluster] = clustersFor(
      SQUARE,
      [planting({ taxon_id: null, canonical_name: null, raw_name: 'Omas Rose' })],
      [colour({ colour: null, months: [] })],
      6,
    );

    expect(cluster!.name).toBe('Omas Rose');
    expect(cluster!.colour).toBeNull();
    expect(cluster!.dots.length).toBeGreaterThan(0);
  });

  it('caps the dots of a very large planting', () => {
    const [cluster] = clustersFor(SQUARE, [planting({ quantity: 500 })], [colour()], 6);
    expect(cluster!.dots).toHaveLength(MAX_DOTS);
  });

  it('draws a cluster the palette has never heard of', () => {
    // A planting added since the palette was last fetched. Grey and present
    // beats missing: the bed is fuller than the last request knew.
    const [cluster] = clustersFor(SQUARE, [planting()], [], 6);
    expect(cluster!.colour).toBeNull();
    expect(cluster!.dots.length).toBeGreaterThan(0);
  });
});

describe('keepInside', () => {
  it('leaves a point that is already in the bed alone', () => {
    expect(keepInside(L_SHAPE, { x: 1, y: 1 })).toEqual({ x: 1, y: 1 });
  });

  it('pulls a point outside back to just inside the edge', () => {
    const at = keepInside(L_SHAPE, { x: 10, y: 1 });
    expect(at.x).toBeCloseTo(6, 1);
    expect(covers(L_SHAPE, at)).toBe(true);
  });

  it('does not leave a cluster in the notch of an L', () => {
    // Clamping to the bounding box would put it at 5,5 — outside the bed but
    // inside the box, which is the one answer that looks right and is wrong.
    const at = keepInside(L_SHAPE, { x: 5, y: 5 });
    expect(covers(L_SHAPE, at)).toBe(true);
    expect(at).not.toEqual({ x: 5, y: 5 });
  });

  it('survives being rounded to centimetres', () => {
    // Found in the running app, not here. The first inset was a millimetre; the
    // position is rounded to centimetres before it is stored, so the inset was
    // rounded away and the cluster came back sitting exactly on the corner of
    // its bed — outside it, by the very test that had just moved it inside.
    const at = keepInside(L_SHAPE, { x: 10, y: 10 });
    const stored = {
      x: Math.round(at.x * 100) / 100,
      y: Math.round(at.y * 100) / 100,
    };
    expect(covers(L_SHAPE, stored)).toBe(true);
  });

  it('lands somewhere a second clamp leaves alone', () => {
    // The reason for the millimetre. Exactly on the line, a point-in-polygon
    // test says "outside", so a clamped cluster failed the check that clamped
    // it and the next drag started the whole dance again.
    const once = keepInside(L_SHAPE, { x: 5, y: 5 });
    expect(keepInside(L_SHAPE, once)).toEqual(once);
  });
});
