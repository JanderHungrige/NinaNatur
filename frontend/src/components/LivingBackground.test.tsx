import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LivingBackground } from './LivingBackground';

describe('LivingBackground', () => {
  it('is hidden from anything that reads the page', () => {
    // Decoration. A screen reader announcing seven leaves would be reading
    // the wallpaper aloud.
    render(<LivingBackground />);
    expect(screen.getByTestId('living-background').getAttribute('aria-hidden')).toBe('true');
  });

  it('starts each leaf part-way through, so they do not arrive in a row', () => {
    const { container } = render(<LivingBackground />);
    const delays = [...container.querySelectorAll('.living__leaf')].map(
      (n) => (n as HTMLElement).style.animationDelay,
    );
    expect(new Set(delays).size).toBeGreaterThan(1);
    expect(delays.filter((d) => d.startsWith('-')).length).toBeGreaterThan(4);
  });

  it('gives each leaf its own pace', () => {
    // Identical durations read as a machine rather than as weather.
    const { container } = render(<LivingBackground />);
    const durations = [...container.querySelectorAll('.living__leaf')].map(
      (n) => (n as HTMLElement).style.animationDuration,
    );
    expect(new Set(durations).size).toBeGreaterThan(3);
  });

  it('draws no more than a background needs', () => {
    // Seven, not seventy. Every one is a composited layer.
    const { container } = render(<LivingBackground />);
    expect(container.querySelectorAll('.living__leaf').length).toBeLessThanOrEqual(12);
  });
});
