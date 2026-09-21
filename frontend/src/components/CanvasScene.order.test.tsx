import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

/*
 * The garden's ground was coloured across the street wherever the plot drawn
 * on the map reached over it: a street is a surface, and sorted by size a long
 * one fell behind the plot (the owner, 2026-09-21). A street is drawn like a
 * building now, and the garden's ground under everything.
 */

type Obstacle = GardenOut['obstacles'][number];

function shape(obstacle_id: number, kind: string, footprint: number[][]): Obstacle {
  return {
    obstacle_id, kind, x: 0, y: 0, shape: 'polygon', width: null, points: footprint,
    constraint_hint: null, height: kind === 'house' ? 8 : null, label: null, roof: 'unknown',
    roof_source: 'user', eaves_m: null, eaves_source: null, roof_fall_deg: null,
    roof_pitch_deg: null, roof_lines: [], height_source: 'user', footprint,
  };
}

const box = (x0: number, y0: number, x1: number, y1: number) =>
  [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

function drawnOrder(obstacles: Obstacle[]): string[] {
  const { container } = render(
    <GardenCanvas
      garden={{
        unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
        share_token: 'tok', name: 'G', latitude: 52.5, longitude: 13.4,
        created_at: '', updated_at: '', beds: [], obstacles,
      }}
      selectedBedId={null} onSelectBed={vi.fn()} size={{ widthPx: 800, heightPx: 600 }}
    />,
  );
  return [...container.querySelectorAll('.obstacle')].map(
    (node) => node.getAttribute('data-kind') ?? node.getAttribute('class') ?? '',
  );
}

const indexOf = (order: string[], kind: string) => order.findIndex((entry) => entry.includes(kind));

describe('CanvasScene — a street is not the garden\'s ground', () => {
  it('draws a street over the garden\'s ground even where the plot reaches across it', () => {
    // A 200 m street is larger than the 25 × 40 m plot, so size alone put it behind.
    const order = drawnOrder([
      shape(1, 'garden', box(0, 0, 25, 40)),
      shape(2, 'street', box(-100, -3, 100, 3)),
    ]);
    expect(indexOf(order, 'garden')).toBeLessThan(indexOf(order, 'street'));
  });

  it('keeps a lawn drawn by the gardener under a street it overlaps', () => {
    const order = drawnOrder([
      shape(1, 'street', box(-10, -3, 10, 3)),
      shape(2, 'lawn', box(-2, -2, 2, 2)),
    ]);
    expect(indexOf(order, 'lawn')).toBeLessThan(indexOf(order, 'street'));
  });

  it('keeps the garden\'s ground under every other surface', () => {
    const order = drawnOrder([
      shape(1, 'lawn', box(-50, -50, 50, 50)),
      shape(2, 'garden', box(0, 0, 25, 40)),
    ]);
    expect(indexOf(order, 'garden')).toBeLessThan(indexOf(order, 'lawn'));
  });
});
