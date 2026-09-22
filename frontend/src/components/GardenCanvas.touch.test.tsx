import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

/*
 * Doc 87, B1 and doc 91, B1 (reported 2026-09-18): on a phone a finger that
 * landed on a house, a street or a bed moved it instead of the plan; a mouse
 * could drag, turn and resize houses and streets; and two fingers did nothing,
 * because nothing handled a second pointer and the plan's `touch-action: none`
 * switched off the browser's own pinch as well.
 */

const HOUSE = 11;
const STREET = 12;
const BED = 21;

function obstacle(id: number, kind: string): GardenOut['obstacles'][number] {
  return {
    obstacle_id: id, kind, x: id === HOUSE ? -10 : 10, y: 10, shape: 'polygon',
    width: null, constraint_hint: null,
    points: [[-3, -2], [3, -2], [3, 2], [-3, 2]],
    height: kind === 'house' ? 7 : null, label: null, roof: 'unknown', roof_source: 'user', eaves_m: null, eaves_source: null,
    roof_fall_deg: null, roof_pitch_deg: null, roof_lines: [],
    height_source: 'user',
    footprint: [[-3, -2], [3, -2], [3, 2], [-3, 2]],
  };
}

function bed(): GardenOut['beds'][number] {
  return {
    bed_id: BED, kind: 'bed', shape: 'polygon', x: 0, y: 0, points: null, width: null,
    constraint_hint: null, name: 'Südbeet', polygon: [[0, -12], [6, -12], [6, -8], [0, -8]],
    soil_type: 'loam', moisture: 'fresh', ellenberg_l: 8, ellenberg_m: 5, ellenberg_n: 5.5,
    ellenberg_r: 6.5, sun_hours: 6.4, slope_deg: null, aspect_deg: null,
    sky_view: null, relative_light: null, expected_sun_h: null, light_computed_at: '2026-08-28T10:00:00+00:00', height_above_ground: 0, label: null, plantings: [],
  };
}

function garden(): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
    share_token: 'tok', name: 'G', latitude: 52.5, longitude: 13.4, created_at: '', updated_at: '',
    beds: [bed()], obstacles: [obstacle(HOUSE, 'house'), obstacle(STREET, 'street')],
  };
}

function show(props: Record<string, unknown> = {}) {
  const calls = { move: vi.fn(), select: vi.fn(), resize: vi.fn(), reshape: vi.fn() };
  render(
    <GardenCanvas
      garden={garden()} selectedBedId={null} onSelectBed={vi.fn()} size={{ widthPx: 800, heightPx: 600 }}
      selectedObstacleId={null} onSelectObstacle={calls.select} onMoveObstacle={calls.move}
      onResizeObstacle={calls.resize} onReshapeObstacle={calls.reshape}
      {...props}
    />,
  );
  return calls;
}

const surface = () => screen.getByTestId('canvas-surface');
const onPlan = (id: number) => document.querySelector(`[data-element-id="${id}"]`) as Element;
/** The plan's span in metres, which is its viewBox's width. */
const span = () => Number((surface().getAttribute('viewBox') ?? '').split(' ')[2]);

/** A drag whose moves arrive where a browser sends them: at the plan, and on up to the window. */
function drag(target: Element, pointerType: string, to: { x: number; y: number }) {
  fireEvent.pointerDown(target, { pointerType, pointerId: 1, button: 0, clientX: 400, clientY: 300 });
  fireEvent.pointerMove(surface(), { pointerType, pointerId: 1, clientX: to.x, clientY: to.y });
  fireEvent.pointerUp(surface(), { pointerType, pointerId: 1, clientX: to.x, clientY: to.y });
}

describe('GardenCanvas — houses and streets stay put', () => {
  it.each([['house', HOUSE], ['street', STREET]])('a mouse cannot drag a %s; the plan pans instead', (_kind, id) => {
    const calls = show();
    const before = surface().getAttribute('viewBox');
    drag(onPlan(id), 'mouse', { x: 500, y: 360 });
    expect(calls.move).not.toHaveBeenCalled();
    expect(surface().getAttribute('viewBox')).not.toBe(before);
  });

  it.each([['house', HOUSE], ['street', STREET]])('a chosen %s wears no handles and no corners', (_kind, id) => {
    show({ selectedObstacleId: id });
    expect(document.querySelectorAll('[data-testid^="handle-"]')).toHaveLength(0);
    expect(document.querySelectorAll('.vertex')).toHaveLength(0);
  });

  it('can still be chosen, to say how tall it is', () => {
    const calls = show();
    fireEvent.click(onPlan(HOUSE));
    expect(calls.select).toHaveBeenCalledWith(HOUSE);
  });

  it('is not chosen by the click that ends a pan begun on it', () => {
    // A mouse sends a click wherever a drag began and ended on the same shape.
    const calls = show();
    drag(onPlan(HOUSE), 'mouse', { x: 460, y: 300 });
    fireEvent.click(onPlan(HOUSE), { clientX: 460, clientY: 300 });
    expect(calls.select).not.toHaveBeenCalled();
  });
});

describe('GardenCanvas — a finger on the plan', () => {
  it('moves the plan, not a bed it has not chosen', () => {
    const calls = show();
    const before = surface().getAttribute('viewBox');
    drag(onPlan(BED), 'touch', { x: 460, y: 340 });
    expect(calls.move).not.toHaveBeenCalled();
    expect(surface().getAttribute('viewBox')).not.toBe(before);
  });

  it('moves a bed once it has been chosen', () => {
    const calls = show({ selectedBedId: BED });
    drag(onPlan(BED), 'touch', { x: 460, y: 340 });
    expect(calls.move).toHaveBeenCalledWith(BED, expect.anything());
  });

  it('leaves a mouse dragging a bed directly, as a desktop always has', () => {
    const calls = show();
    drag(onPlan(BED), 'mouse', { x: 460, y: 340 });
    expect(calls.move).toHaveBeenCalledWith(BED, expect.anything());
  });
});

describe('GardenCanvas — two fingers', () => {
  const finger = (
    type: 'pointerDown' | 'pointerMove' | 'pointerUp',
    pointerId: number,
    x: number,
    target: Element = surface(),
  ) => fireEvent[type](target, { pointerType: 'touch', pointerId, clientX: x, clientY: 300 });

  it('spreading them zooms in, between them', () => {
    show();
    const before = span();
    finger('pointerDown', 1, 300);
    finger('pointerDown', 2, 500);
    finger('pointerMove', 2, 700); // 200 px apart, then 400
    finger('pointerUp', 2, 700);
    finger('pointerUp', 1, 300);
    expect(span()).toBeCloseTo(before / 2, 1);
  });

  it('pinching them together zooms out', () => {
    show();
    const before = span();
    finger('pointerDown', 1, 300);
    finger('pointerDown', 2, 700);
    finger('pointerMove', 2, 500); // 400 px apart, then 200
    finger('pointerUp', 2, 500);
    finger('pointerUp', 1, 300);
    expect(span()).toBeCloseTo(before * 2, 1);
  });

  it('zooms once when Safari sends its own gesture for the same pinch', () => {
    // On an iPhone the pinch arrives as touches *and* as gesturechange; both
    // zoomed, so a spread to twice the distance zoomed four times over.
    show();
    const before = span();
    finger('pointerDown', 1, 300);
    finger('pointerDown', 2, 500);
    finger('pointerMove', 2, 700);
    const gesture = Object.assign(new Event('gesturechange', { cancelable: true }),
      { scale: 2, clientX: 500, clientY: 300 });
    act(() => { surface().dispatchEvent(gesture); });
    finger('pointerUp', 2, 700);
    finger('pointerUp', 1, 300);
    expect(gesture.defaultPrevented).toBe(true);
    expect(span()).toBeCloseTo(before / 2, 1);
  });

  it('keeps the plan when a gesture comes without a position', () => {
    show();
    const gesture = Object.assign(new Event('gesturechange', { cancelable: true }), { scale: 2 });
    act(() => { surface().dispatchEvent(gesture); });
    expect(Number.isFinite(span())).toBe(true);
    expect((surface().getAttribute('viewBox') ?? '').split(' ').every((n) => Number.isFinite(Number(n))))
      .toBe(true);
  });

  it('a second finger ends whatever the first was dragging', () => {
    const calls = show({ selectedBedId: BED });
    finger('pointerDown', 1, 400, onPlan(BED));
    finger('pointerDown', 2, 600);
    finger('pointerMove', 2, 760);
    finger('pointerUp', 2, 760);
    finger('pointerUp', 1, 400);
    expect(calls.move).not.toHaveBeenCalled();
  });
});
