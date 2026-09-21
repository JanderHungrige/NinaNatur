import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { garden, shed } from '../testing/gardens';
import { PlanThemeProvider } from '../themes/context';
import { draftSketch } from '../themes/draft-sketch';
import { technisch } from '../themes/technisch';
import type { PlanTheme } from '../themes/types';
import { GardenCanvas } from './GardenCanvas';
import { drawsOpenStreetMap, PlanCredit } from './PlanCredit';

/*
 * OpenStreetMap's credit beneath the plan (owner's check, 2026-09-21, #10): a
 * garden made from the map draws OSM's streets and house outlines, and ODbL
 * asks for the credit where they are shown.
 */

const street = shed({ obstacle_id: 7, kind: 'street', label: 'Hauptstraße', height: null });
const mapHouse = shed({
  obstacle_id: 8, kind: 'house', height_source: 'osm_levels', roof_source: 'osm', outline_source: 'osm',
});
const CREDIT = 'Karte: © OpenStreetMap-Mitwirkende';

describe('what of the plan is OpenStreetMap\'s', () => {
  it('is a street, or an outline the map import brought', () => {
    expect(drawsOpenStreetMap({ obstacles: [street] })).toBe(true);
    expect(drawsOpenStreetMap({ obstacles: [mapHouse] })).toBe(true);
  });

  it('stays the map\'s when the gardener corrects its height and roof', () => {
    // The outline the plan draws is still OpenStreetMap's (review, 2026-09-21).
    const corrected = { ...mapHouse, height_source: 'user', roof_source: 'user', eaves_source: null };
    expect(drawsOpenStreetMap({ obstacles: [corrected] })).toBe(true);
  });

  it('is nothing the gardener drew', () => {
    expect(drawsOpenStreetMap({ obstacles: [] })).toBe(false);
    expect(drawsOpenStreetMap({ obstacles: [shed()] })).toBe(false);
    // A tree found in the laser and accepted is measured, and no building.
    const tree = shed({ kind: 'tree', height_source: 'measured', roof_source: 'user' });
    expect(drawsOpenStreetMap({ obstacles: [tree] })).toBe(false);
    // A house drawn by hand is the gardener's whatever a survey later measured.
    const surveyed = shed({ kind: 'house', height_source: 'surveyed', roof_source: 'surveyed' });
    expect(drawsOpenStreetMap({ obstacles: [surveyed] })).toBe(false);
  });
});

function caption(theme: PlanTheme, obstacles = [street]) {
  return render(
    <PlanThemeProvider theme={theme}><PlanCredit garden={{ obstacles }} /></PlanThemeProvider>,
  );
}

describe('the map\'s credit beneath the plan', () => {
  it('names OpenStreetMap under a Technisch plan that draws its streets, linked to its terms', () => {
    const { container } = caption(technisch);
    expect(container.textContent).toBe(CREDIT);
    const link = screen.getByRole('link', { name: '© OpenStreetMap-Mitwirkende' });
    expect(link.getAttribute('href')).toBe('https://www.openstreetmap.org/copyright');
  });

  it('stands on a line of its own under the style\'s credit', () => {
    const { container } = caption(draftSketch);
    const lines = [...container.querySelectorAll('.plan-credit')].map((line) => line.textContent);
    expect(lines).toHaveLength(2);
    expect(lines[0]).toContain('Draft Sketch');
    expect(lines[1]).toBe(CREDIT);
  });

  it('says nothing for a garden drawn by hand in a theme of our own', () => {
    expect(caption(technisch, [shed()]).container.textContent).toBe('');
  });

  it('is given by the plan itself, beneath the drawing', () => {
    const { container } = render(
      <PlanThemeProvider theme={technisch}>
        <GardenCanvas garden={garden('tok', 'Kartengarten', { obstacles: [street] })}
                      selectedBedId={null} onSelectBed={() => {}} />
      </PlanThemeProvider>,
    );
    const credit = container.querySelector('.plan-credit');
    expect(credit?.textContent).toBe(CREDIT);
    expect(container.querySelector('.canvas-stage')?.contains(credit)).toBe(false);
  });
});
