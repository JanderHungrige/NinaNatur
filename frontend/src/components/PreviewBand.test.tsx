import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PreviewBand } from './PreviewBand';

describe('PreviewBand', () => {
  it('says nothing at all on production', () => {
    // The site that matters most is the one that must not be labelled. A band
    // there would be noise, and it is also what would appear by mistake.
    const { container } = render(<PreviewBand environment="prod" />);
    expect(container.innerHTML).toBe('');
  });

  it('says nothing when the server did not say', () => {
    // An older image, or a cached health response. Defaulting to a band would
    // put "Vorschau" across the live site the first time anything went odd.
    const { container } = render(<PreviewBand environment={null} />);
    expect(container.innerHTML).toBe('');
  });

  it('names the environment and warns that gardens are not kept', () => {
    render(<PreviewBand environment="dev" />);

    expect(screen.getByText(/Vorschau \(dev\)/)).toBeDefined();
    expect(screen.getByText(/nicht aufgehoben/)).toBeDefined();
  });

  it('points at the real site, so somebody can move', () => {
    render(<PreviewBand environment="dev" />);

    const link = screen.getByRole('link', { name: /ninanatur\.w3rth\.de/ });
    expect(link.getAttribute('href')).toBe('https://ninanatur.w3rth.de');
  });

  it('labels any environment, not just the one that exists today', () => {
    // A third stack is already planned. It must not need a code change to be
    // marked as not-production.
    render(<PreviewBand environment="zentrale" />);
    expect(screen.getByText(/Vorschau \(zentrale\)/)).toBeDefined();
  });

  it('announces itself to a screen reader without stealing focus', () => {
    render(<PreviewBand environment="dev" />);
    expect(screen.getByRole('status')).toBeDefined();
  });
});
