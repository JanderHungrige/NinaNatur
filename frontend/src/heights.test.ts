import { describe, expect, it } from 'vitest';
import { HEIGHT_SOURCES, eavesNote, heightNote, isMeasured, roofNote } from './heights';

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

describe('roofNote — where a roof shape came from (doc 93)', () => {
  it('names the survey and OpenStreetMap', () => {
    expect(roofNote('gable', 'surveyed')).toBe('amtlich vermessen');
    expect(roofNote('hip', 'osm')).toBe('aus OpenStreetMap');
  });

  it('says nothing about the gardener\'s own answer, or about no answer', () => {
    expect(roofNote('gable', 'user')).toBeNull();
    expect(roofNote('unknown', 'surveyed')).toBeNull();
  });
});

describe('eavesNote — where an eaves height came from (doc 93)', () => {
  it('uses the words the heights already use', () => {
    expect(eavesNote(6.2, 'surveyed', 9.5)).toBe(heightNote('surveyed'));
    expect(eavesNote(6, 'osm_levels', 9)).toBe(heightNote('osm_levels'));
  });

  it('says what is assumed when nobody gave them, with the number when it can', () => {
    expect(eavesNote(null, null, 9)).toBe(
      'Nicht bekannt: gerechnet wird mit drei Vierteln der Firsthöhe, 6,8 m',
    );
    expect(eavesNote(null, null, null)).toBe(
      'Nicht bekannt: gerechnet wird mit drei Vierteln der Firsthöhe',
    );
  });

  it('says nothing about the gardener\'s own number', () => {
    expect(eavesNote(5, 'user', 9)).toBeNull();
  });

  it('owns up to a number whose origin nobody kept', () => {
    expect(eavesNote(6.2, null, 9)).toBe('Herkunft nicht vermerkt');
  });
});
