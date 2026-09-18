import { describe, expect, it } from 'vitest';

import { ridgeNote } from './roofs';

describe('ridgeNote — which way the ridge runs, and the pitch (doc 94)', () => {
  it('names a surveyed ridge by the compass, with the pitch', () => {
    expect(ridgeNote('gable', 0, 38.2)).toBe('First Ost–West (amtlich vermessen) · Neigung 38°');
    expect(ridgeNote('gable', 90, 30)).toBe('First Nord–Süd (amtlich vermessen) · Neigung 30°');
    expect(ridgeNote('hip', 45, 22)).toBe('First Südost–Nordwest (amtlich vermessen) · Neigung 22°');
    expect(ridgeNote('gable', 135, 40)).toBe('First Nordost–Südwest (amtlich vermessen) · Neigung 40°');
  });

  it('says the ridge is assumed where the survey has not said', () => {
    expect(ridgeNote('gable', null, 27.6)).toBe(
      'First entlang der längeren Seite (angenommen) · Neigung 28°',
    );
  });

  it('says which way a pent falls, or that it is taken as flat', () => {
    expect(ridgeNote('pent', 0, 12)).toBe('Fällt nach Norden (amtlich vermessen) · Neigung 12°');
    expect(ridgeNote('pent', 200, 9)).toBe('Fällt nach Süden (amtlich vermessen) · Neigung 9°');
    expect(ridgeNote('pent', 315, 9)).toBe('Fällt nach Nordwesten (amtlich vermessen) · Neigung 9°');
    expect(ridgeNote('pent', null, null)).toBe('Gefälle unbekannt: gerechnet wie ein Flachdach');
  });

  it('leaves the pitch out when there is none to give', () => {
    expect(ridgeNote('gable', 0, null)).toBe('First Ost–West (amtlich vermessen)');
  });

  it('says nothing about a roof without one ridge', () => {
    for (const roof of ['flat', 'mix', 'other', 'unknown']) {
      expect(ridgeNote(roof, 0, 10)).toBeNull();
    }
  });
});
