import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { SourceCredits } from './SourceCredits';

/* The credits a garden's numbers oblige it to show (doc 106). */

const GROUND = {
  about: 'ground',
  name: 'Geländemodell Bayern',
  licence: 'CC-BY-4.0',
  attribution: 'Datenquelle: Bayerische Vermessungsverwaltung – www.geodaten.bayern.de',
  detail: '1 m, ±0.01 m',
};
const HORIZON = {
  about: 'horizon',
  name: 'Copernicus GLO-30',
  licence: 'Copernicus',
  attribution: 'Copernicus DEM GLO-30 … © DLR e.V. … © Airbus … ESA',
  detail: '30 m',
};

describe('where the numbers come from', () => {
  it('names each source, what it decided and how fine it is', () => {
    render(<SourceCredits credits={[GROUND]} />);
    expect(screen.getByText(/Gelände: Geländemodell Bayern/)).toBeDefined();
    expect(screen.getByText(/1 m, ±0.01 m/)).toBeDefined();
  });

  it('prints the credit word for word, because the licence asks for it', () => {
    render(<SourceCredits credits={[GROUND, HORIZON]} />);
    expect(screen.getByText(GROUND.attribution)).toBeDefined();
    expect(screen.getByText(HORIZON.attribution)).toBeDefined();
  });

  it('says in German what one survey decided when it decided two things', () => {
    render(<SourceCredits credits={[{ ...GROUND, about: 'ground, buildings' }]} />);
    expect(screen.getByText(/Gelände und Gebäude:/)).toBeDefined();
  });

  it('and draws nothing at all for a garden that rests on nothing', () => {
    const { container } = render(<SourceCredits credits={[]} />);
    expect(container.innerHTML).toBe('');
  });
});
