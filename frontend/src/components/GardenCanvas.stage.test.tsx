import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { GardenCanvas } from './GardenCanvas';

function garden(): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
    share_token: 'tok',
    name: 'Testgarten',
    latitude: 52.5,
    longitude: 13.4,
    created_at: '',
    updated_at: '',
    beds: [],
    obstacles: [],
  };
}

function box(width: number, height: number): DOMRect {
  return { x: 0, y: 0, left: 0, top: 0, right: width, bottom: height, width, height, toJSON: () => ({}) };
}

/** Stands in for the browser's observer, and remembers what it was asked to watch. */
class FakeObserver {
  static watched: Element[] = [];
  static instances: FakeObserver[] = [];
  readonly callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    FakeObserver.instances.push(this);
  }

  observe(target: Element): void {
    FakeObserver.watched.push(target);
  }

  unobserve(): void {}

  disconnect(): void {}

  /** What the browser does when a watched box changes size. */
  fire(): void {
    this.callback([], this as unknown as ResizeObserver);
  }
}

describe('GardenCanvas — the stage owns the plan’s height', () => {
  let stageHeight = 320;

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    FakeObserver.watched = [];
    FakeObserver.instances = [];
  });

  function mount(height = 320): Element {
    stageHeight = height;
    vi.stubGlobal('ResizeObserver', FakeObserver);
    // jsdom lays nothing out, so every box is told its size. The drawing is told
    // the collapsed strip the bug produced; the stage is told the box the page
    // gives the plan. Only the stage's answer may count.
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (
      this: Element,
    ) {
      if (this.classList.contains('canvas-stage')) return box(900, stageHeight);
      if (this.tagName.toLowerCase() === 'svg') return box(900, 12);
      return box(0, 0);
    });
    render(<GardenCanvas garden={garden()} selectedBedId={null} onSelectBed={vi.fn()} />);
    return screen.getByTestId('canvas-surface');
  }

  function shapeOf(surface: Element): number {
    const [, , width, height] = (surface.getAttribute('viewBox') ?? '').split(' ').map(Number);
    return (height ?? Number.NaN) / (width ?? Number.NaN);
  }

  it('watches the stage the plan sits in, not the drawing', () => {
    const surface = mount();
    expect(FakeObserver.watched.some((el) => el.classList.contains('canvas-stage'))).toBe(true);
    expect(FakeObserver.watched).not.toContain(surface);
  });

  it('takes its shape from the stage even while the drawing measures a strip', () => {
    expect(shapeOf(mount(320))).toBeCloseTo(320 / 900, 6);
  });

  it('grows back when the window does', () => {
    // Opened in a short window, then maximised — the wave's manual check, as far
    // as jsdom can take it.
    const surface = mount(256);
    stageHeight = 675;
    act(() => {
      for (const observer of FakeObserver.instances) observer.fire();
    });
    expect(shapeOf(surface)).toBeCloseTo(675 / 900, 6);
  });
});
