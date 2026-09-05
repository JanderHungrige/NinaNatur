import { describe, expect, it } from 'vitest';
import { FLAT_BELOW_DEG, slopeName, slopePercent, slopeSentence } from './slopes';

describe('slopeName', () => {
  it('turns a bearing into the word for the hillside', () => {
    expect(slopeName(180)).toBe('Südhang');
    expect(slopeName(0)).toBe('Nordhang');
    expect(slopeName(90)).toBe('Osthang');
    expect(slopeName(270)).toBe('Westhang');
  });

  it('rounds to the nearest of the eight points', () => {
    expect(slopeName(160)).toBe('Südhang');
    expect(slopeName(200)).toBe('Südhang');
    expect(slopeName(210)).toBe('Südwesthang');
  });

  it('wraps rather than falling off either end', () => {
    // 350° is north, and an index that ran off the array would be undefined.
    expect(slopeName(350)).toBe('Nordhang');
    expect(slopeName(359.9)).toBe('Nordhang');
    expect(slopeName(-10)).toBe('Nordhang');
  });

  it('says nothing when there is nothing to say', () => {
    expect(slopeName(null)).toBeNull();
  });
});

describe('slopePercent', () => {
  it('is the gradient, not the angle', () => {
    // 45° is a 100 % slope, which is the one everybody gets wrong.
    expect(slopePercent(45)).toBe(100);
    expect(slopePercent(5)).toBe(9);
    expect(slopePercent(0)).toBe(0);
  });
});

describe('slopeSentence', () => {
  it('is a direction and a gradient', () => {
    expect(slopeSentence(5, 180)).toBe('Südhang, 9 %');
  });

  it('calls level ground level', () => {
    expect(slopeSentence(1, 180)).toBe('eben');
    expect(FLAT_BELOW_DEG).toBe(2);
  });

  it('says nothing at all about ground nobody has measured', () => {
    // Not "eben". A garden nobody has looked at is not a flat garden, and
    // saying so would be the same false confidence the flat model had.
    expect(slopeSentence(null, null)).toBeNull();
  });

  it('gives the gradient alone when the direction is missing', () => {
    expect(slopeSentence(5, null)).toBe('9 % Gefälle');
  });
});
