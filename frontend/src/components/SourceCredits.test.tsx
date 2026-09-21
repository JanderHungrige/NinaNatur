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

  it('credits OpenStreetMap for the map, linked to its terms (2026-09-21)', () => {
    render(<SourceCredits credits={[{
      about: 'map', name: 'OpenStreetMap', licence: 'ODbL-1.0',
      attribution: '© OpenStreetMap-Mitwirkende', detail: null,
    }]} />);
    expect(screen.getByText('Karte: OpenStreetMap')).toBeDefined();
    const link = screen.getByRole('link', { name: '© OpenStreetMap-Mitwirkende' });
    expect(link.getAttribute('href')).toBe('https://www.openstreetmap.org/copyright');
  });

  it('says what the laser decided in German too, and links no credit that asks for none', () => {
    render(<SourceCredits credits={[{
      about: 'laser', name: 'Laserscan Nordrhein-Westfalen', licence: 'dl-de/zero-2-0',
      attribution: 'Geobasis NRW', detail: '4 Punkte/m²',
    }]} />);
    expect(screen.getByText(/^Baumkronen: Laserscan Nordrhein-Westfalen/)).toBeDefined();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('and draws nothing at all for a garden that rests on nothing', () => {
    const { container } = render(<SourceCredits credits={[]} />);
    expect(container.innerHTML).toBe('');
  });
});
