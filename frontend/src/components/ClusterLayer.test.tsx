import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { Cluster } from '../canvas/clusters';
import { ClusterLayer } from './ClusterLayer';

function cluster(overrides: Partial<Cluster> = {}): Cluster {
  return {
    plantingId: 1,
    taxonId: 7,
    name: 'Salvia pratensis',
    centre: { x: 2, y: 2 },
    radius: 0.6,
    colour: 'violet',
    dots: [
      { x: 2, y: 2, r: 0.1 },
      { x: 2.2, y: 1.9, r: 0.08 },
    ],
    ...overrides,
  };
}

function show(clusters: Cluster[], props: Record<string, unknown> = {}) {
  const onSelectCluster = vi.fn();
  const onShowInfo = vi.fn();
  const { container } = render(
    <svg>
      <ClusterLayer
        clusters={clusters}
        onSelectCluster={onSelectCluster}
        onShowInfo={onShowInfo}
        spacing={1}
        {...props}
      />
    </svg>,
  );
  return { container, onSelectCluster, onShowInfo };
}

describe('ClusterLayer', () => {
  it('draws a group per patch with its dots', () => {
    const { container } = show([cluster(), cluster({ plantingId: 2 })]);
    expect(container.querySelectorAll('.cluster')).toHaveLength(2);
    expect(container.querySelectorAll('.bloom-dot')).toHaveLength(4);
  });

  it('paints a flowering patch in its colour and a resting one in grey', () => {
    const { container } = show([cluster(), cluster({ plantingId: 2, colour: null })]);
    const dots = [...container.querySelectorAll('.bloom-dot')];

    expect(dots[0]!.getAttribute('fill')).not.toBe('var(--ink-muted)');
    expect(dots[2]!.getAttribute('fill')).toBe('var(--ink-muted)');
  });

  it('falls back to grey for a colour it has no swatch for', () => {
    // The catalogue is several sources deep and may one day say something this
    // list does not cover. Grey is wrong-ish; a crash or a blank is worse.
    const { container } = show([cluster({ colour: 'chartreuse' })]);
    expect(container.querySelector('.bloom-dot')!.getAttribute('fill')).toBe(
      'var(--ink-muted)',
    );
  });

  it('gives each patch something big enough to click', () => {
    // A dot is two centimetres across in garden metres. Chasing that with a
    // mouse is not a gesture anybody can perform.
    const { container } = show([cluster({ radius: 0.05 })]);
    const reach = container.querySelector('.cluster__reach')!;
    expect(Number(reach.getAttribute('r'))).toBeGreaterThanOrEqual(0.35);
  });

  it('selects a patch when it is clicked', () => {
    const { container, onSelectCluster } = show([cluster()]);
    fireEvent.click(container.querySelector('.cluster')!);
    expect(onSelectCluster).toHaveBeenCalledWith(1);
  });

  it('names the selected patch on the plan', () => {
    show([cluster()], { selectedPlantingId: 1 });
    expect(screen.getByTestId('cluster-tag').textContent).toContain('Salvia pratensis');
  });

  it('names nothing while nothing is selected', () => {
    show([cluster()]);
    expect(screen.queryByTestId('cluster-tag')).toBeNull();
  });

  it('opens the info panel from the tag', () => {
    const { onShowInfo } = show([cluster()], { selectedPlantingId: 1 });
    fireEvent.click(screen.getByRole('button', { name: /Info zu Salvia pratensis/ }));
    expect(onShowInfo).toHaveBeenCalledWith(7, 'Salvia pratensis');
  });

  it('offers no info for a plant the catalogue cannot name', () => {
    // There is nothing to look up. A button that opens an empty panel is worse
    // than no button.
    show([cluster({ taxonId: null, name: 'Omas Rose' })], { selectedPlantingId: 1 });
    expect(screen.queryByRole('button', { name: /Info zu/ })).toBeNull();
    expect(screen.getByTestId('cluster-tag').textContent).toContain('Omas Rose');
  });

  it('scales its text with the zoom', () => {
    // The viewBox is in metres, so a fixed font size would be a fixed number of
    // metres tall — unreadable zoomed out, enormous zoomed in.
    show([cluster()], { selectedPlantingId: 1, spacing: 4 });
    const name = screen.getByTestId('cluster-tag').querySelector('text')!;
    expect(Number(name.getAttribute('font-size'))).toBeCloseTo(4 * 0.42, 5);
  });
});
