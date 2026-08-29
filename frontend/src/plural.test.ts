import { describe, expect, it } from 'vitest';

import { bedName, beds, objects, obstacles } from './plural';

describe('German plurals', () => {
  it('uses the singular for exactly one', () => {
    expect(beds(1)).toBe('1 Beet');
    expect(obstacles(1)).toBe('1 Hindernis');
  });

  it('uses the plural for zero and for many', () => {
    expect(beds(0)).toBe('0 Beete');
    expect(beds(4)).toBe('4 Beete');
    expect(obstacles(0)).toBe('0 Hindernisse');
    expect(obstacles(3)).toBe('3 Hindernisse');
  });
});

describe('bedName', () => {
  it('does not say Beet twice', () => {
    // The drawing tool names beds "Beet 1", and the label prepended "Beet " —
    // screen readers got "Beet Beet 1". Visible the moment a bed was drawn.
    expect(bedName('Beet 1')).toBe('Beet 1');
  });

  it('labels a bare name so it is not read as an unlabelled shape', () => {
    expect(bedName('Südseite')).toBe('Beet Südseite');
  });

  it('ignores case and surrounding space', () => {
    expect(bedName('  beet am Zaun ')).toBe('  beet am Zaun ');
  });

  it('does not match a name that merely starts with those letters', () => {
    expect(bedName('Beetenrand')).toBe('Beet Beetenrand');
  });
});

describe('objects', () => {
  it('uses the singular for one', () => {
    // "1 Objekt(en)" was the fifth appearance of this dodge in this codebase.
    expect(objects(1)).toBe('1 Objekt');
  });

  it('uses the plural for more', () => {
    expect(objects(4)).toBe('4 Objekte');
  });
});
