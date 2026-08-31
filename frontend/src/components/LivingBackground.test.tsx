import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LivingBackground } from './LivingBackground';

describe('LivingBackground', () => {
  it('is hidden from anything that reads the page', () => {
    // Decoration. A screen reader announcing a particle field would be reading
    // the wallpaper aloud.
    render(<LivingBackground />);
    expect(screen.getByTestId('living-background').getAttribute('aria-hidden')).toBe('true');
  });

  it('draws the field as layers, not as hundreds of nodes', () => {
    // Each layer carries its whole field of motes in one background image. A
    // node per particle would be a composited layer per particle.
    const { container } = render(<LivingBackground />);
    expect(container.querySelectorAll('.living__layer')).toHaveLength(3);
    expect(container.querySelectorAll('.living__bokeh').length).toBeLessThanOrEqual(8);
  });

  it('gives the layers different depths to move at', () => {
    // Identical speeds are a flat sheet of dots. The parallax is the depth.
    const { container } = render(<LivingBackground />);
    for (const depth of ['far', 'mid', 'near']) {
      expect(container.querySelector(`.living__layer--${depth}`)).not.toBeNull();
    }
  });

  it('lights the field from above and gives it a floor to rise from', () => {
    // Without the floor the motes merely exist; with it they are coming from
    // somewhere, which is what the reference picture is doing.
    const { container } = render(<LivingBackground />);
    expect(container.querySelector('.living__glow')).not.toBeNull();
    expect(container.querySelector('.living__floor')).not.toBeNull();
  });
});
