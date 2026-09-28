import { describe, expect, it } from 'vitest';

import type { ShadowMark } from './api/client';
import { localToIso, nowLocal, readingWords, seenWords } from './shadowMarks';

/* The tests run on the gardeners' clock, Europe/Berlin (vitest.config.ts): in
   UTC a test could not tell local time from UTC. */

type Reading = NonNullable<ShadowMark['reading']>;

function mark(reading: Partial<Reading> | null): ShadowMark {
  const base: Reading = {
    altitude: 38, azimuth: 180, rings: [], nearest: [0, 0], offset_m: 0.8, edge: 'far',
    model_longer: false, along_m: -0.8, across_m: 0, height_m: -0.63, turned_deg: null,
  };
  return {
    mark_id: 1, element_id: 2, x: 0, y: 0, seen_at: '2026-06-21T09:30:00+00:00',
    reading: reading === null ? null : { ...base, ...reading },
  };
}

describe('readingWords — what a shadow mark found (doc 122)', () => {
  it('reads a shadow seen further than the model casts it as a thing too low', () => {
    expect(readingWords(mark({}))).toBe(
      'Das Modell wirft den Schatten 0,8 m zu kurz — als stünde es 0,6 m zu niedrig.');
  });

  it('reads one seen shorter as a thing too tall', () => {
    expect(readingWords(mark({ model_longer: true, along_m: 1.2, offset_m: 1.2,
                               height_m: 0.94 }))).toBe(
      'Das Modell wirft den Schatten 1,2 m zu weit — als stünde es 0,9 m zu hoch.');
  });

  it('gives no height too small to measure', () => {
    // A low sun turns a 20 cm miss into a height of 3 cm (review, 2026-09-28).
    expect(readingWords(mark({ offset_m: 0.2, height_m: -0.03 }))).toBe(
      'Das Modell wirft den Schatten 0,2 m zu kurz.');
  });

  it('reads where a shadow begins as its beginning, never as a height', () => {
    // A crown's shadow begins where its base casts, not its top: "zu kurz, zu
    // hoch" both at once was what the page said there (review, 2026-09-28).
    expect(readingWords(mark({ edge: 'near', model_longer: true, height_m: null }))).toBe(
      'Im Modell beginnt der Schatten 0,8 m früher.');
    expect(readingWords(mark({ edge: 'near', model_longer: false, height_m: null }))).toBe(
      'Im Modell beginnt der Schatten 0,8 m später.');
  });

  it('reads a miss round the thing as a turn, and asks about the plan\'s north', () => {
    const turned = mark({ edge: 'side', height_m: null, turned_deg: 4.4, offset_m: 1.5 });
    expect(readingWords(turned)).toBe(
      'Das Modell wirft den Schatten 1,5 m seitlich daneben — um 4° gegen den Uhrzeigersinn '
      + 'verdreht. Stimmt die Nordrichtung des Plans?');
    expect(readingWords(mark({ edge: 'side', height_m: null, turned_deg: -0.6, offset_m: 0.2 })))
      .toContain('um 0,6° im Uhrzeigersinn verdreht');
  });

  it('says only that it misses beside, where the miss is no turn', () => {
    expect(readingWords(mark({ edge: 'side', height_m: null, turned_deg: null, offset_m: 4 })))
      .toBe('Das Modell wirft den Schatten 4,0 m seitlich daneben.');
  });

  it('says the model meets the edge within a shadow\'s blur', () => {
    expect(readingWords(mark({ offset_m: 0.04 }))).toBe('Das Modell trifft die Schattenkante.');
  });

  it('says so when there is nothing to read any more', () => {
    expect(readingWords(mark(null))).toBe(
      'Dieses Element wirft zu diesem Zeitpunkt keinen Schatten mehr.');
  });
});

describe('the moment of a mark, on a Berlin clock', () => {
  it('shows now as the field holds it, to the minute', () => {
    expect(nowLocal(new Date('2026-09-28T07:05:42Z'))).toBe('2026-09-28T09:05');
  });

  it('sends the moment the field names in UTC, and nothing for an empty field', () => {
    expect(localToIso('2026-06-21T11:30')).toBe('2026-06-21T09:30:00.000Z');
    expect(localToIso('')).toBeNull();
    expect(localToIso('gestern')).toBeNull();
  });

  it('says when it was seen on the gardener\'s clock', () => {
    expect(seenWords('2026-06-21T09:30:00+00:00')).toBe('21.06.2026, 11:30');
  });
});
