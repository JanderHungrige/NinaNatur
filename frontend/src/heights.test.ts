import { describe, expect, it } from 'vitest';
import { HEIGHT_SOURCES, heightNote, isMeasured } from './heights';

describe('heightNote', () => {
  it('says how a height was arrived at', () => {
    expect(heightNote('surveyed')).toBe('amtlich vermessen');
    expect(heightNote('measured')).toBe('aus Laserdaten gemessen');
    expect(heightNote('osm_levels')).toBe('aus Geschosszahl geschätzt');
    expect(heightNote('neighbourhood')).toBe('für die Gegend angenommen');
  });

  it('says nothing about what the user typed themselves', () => {
    // They know they typed it. A badge saying "you said so" on the one value
    // somebody is sure about is noise.
    expect(heightNote('user')).toBeNull();
  });

  it('shows a value it does not recognise rather than hiding it', () => {
    // A server that starts sending a new source should not quietly look like a
    // user entry — which is the one state that means "do not overwrite".
    expect(heightNote('lidar_2027')).toBe('lidar_2027');
  });

  it('says nothing when the server said nothing', () => {
    expect(heightNote(null)).toBeNull();
    expect(heightNote(undefined)).toBeNull();
  });
});

describe('isMeasured', () => {
  it('separates the two measurements from the three guesses', () => {
    expect(isMeasured('surveyed')).toBe(true);
    expect(isMeasured('measured')).toBe(true);
    for (const guess of ['osm_height', 'osm_levels', 'neighbourhood', 'user']) {
      expect(isMeasured(guess)).toBe(false);
    }
  });
});

describe('the vocabulary', () => {
  it('covers every source the server has', () => {
    // Mirrors HeightSource in surroundings.py. Two lists of the same thing
    // drift, and the kind vocabulary already taught this once.
    expect(Object.keys(HEIGHT_SOURCES).sort()).toEqual(
      ['measured', 'neighbourhood', 'osm_height', 'osm_levels', 'surveyed', 'user'],
    );
  });
});
