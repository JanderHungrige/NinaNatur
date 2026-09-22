import { describe, expect, it } from 'vitest';

import { bed } from '../testing/gardens';
import { lightText } from './BedPanel';

/*
 * What the sky adds to a bed's line (doc 118): the sunshine to expect with the
 * climate's cloud, the share of the sky it sees, and its light as a share of
 * open ground's. The light value is still the hours' until that is decided.
 */

describe('a bed line with its sky', () => {
  it('says what the sky adds between the hours and the light value', () => {
    const text = lightText(bed({
      sun_hours: 4.0, ellenberg_l: 6.25, slope_deg: null, aspect_deg: null,
      sky_view: 0.6, relative_light: 0.47, expected_sun_h: 1.75,
    }));
    expect(text).toBe(
      '4.0 h/Tag · erwartbar 1.8 h · sieht 60 % des Himmels · 47 % des Freilandlichts · L 6.3');
  });

  it('says only what it knows on a bed computed before the sky counted', () => {
    const text = lightText(bed({
      sun_hours: 4.0, ellenberg_l: 6.25, slope_deg: null, aspect_deg: null,
      sky_view: null, relative_light: null, expected_sun_h: null,
    }));
    expect(text).toBe('4.0 h/Tag · L 6.3');
  });
});
