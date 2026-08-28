import { describe, expect, it } from 'vitest';

import { beds, obstacles } from './plural';

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
