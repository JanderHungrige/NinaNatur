import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { KINDS } from '../kinds';
import { GardenCanvas } from './GardenCanvas';

function obstacle(
  kind: string,
  id: number,
): GardenOut['obstacles'][number] {
  return {
    obstacle_id: id,
    kind,
    x: id * 12,
    y: 0,
    shape: 'rect',
    width: 4,
    depth: 3,
    rotation: 0,
    points: null,
    height: 2,
    label: null,
    height_source: 'user',
    footprint: [[-2, 1.5], [2, 1.5], [2, -1.5], [-2, -1.5]],
  };
}

function garden(obstacles: GardenOut['obstacles']): GardenOut {
  return {
    unidentified_plantings: 0,
    share_token: 'tok',
    name: 'Testgarten',
    latitude: 52.5,
    longitude: 13.4,
    created_at: '',
    updated_at: '',
    beds: [],
    obstacles,
  };
}

function show(obstacles: GardenOut['obstacles']) {
  return render(
    <GardenCanvas
      garden={garden(obstacles)}
      selectedBedId={null}
      onSelectBed={vi.fn()}
      size={{ widthPx: 800, heightPx: 600 }}
      onSelectObstacle={vi.fn()}
    />,
  ).container;
}

describe('CanvasScene — how the plan looks', () => {
  it('draws every kind as the symbol its vocabulary names', () => {
    const container = show(KINDS.map((k, i) => obstacle(k.kind, i + 1)));
    for (const kind of KINDS) {
      const drawn = container.querySelector(`.obstacle--${kind.kind}`);
      expect(drawn, `nothing drawn for ${kind.kind}`).not.toBeNull();
      expect(drawn?.getAttribute('fill')).toBe(`url(#symbol-${kind.symbol})`);
    }
  });

  it('defines each texture once, not once per object', () => {
    // Six paving slabs are one slab pattern. A pattern per object is a
    // defs block that grows with the garden.
    const container = show([obstacle('paving', 1), obstacle('paving', 2), obstacle('paving', 3)]);
    expect(container.querySelectorAll('#symbol-slabs')).toHaveLength(1);
  });

  it('keeps every object reachable, named and clickable', () => {
    // Legibility outranks prettiness: a plan nobody can tab through is a
    // picture, not a tool.
    show([obstacle('pond', 1), obstacle('tree', 2)]);
    for (const name of [/Teich/, /Baum|Eiche/]) {
      const node = screen.getByRole('button', { name });
      expect(node.getAttribute('tabindex')).toBe('0');
    }
  });

  it('lets the pointer through the decoration to the object beneath', () => {
    // Texture is drawn, not clicked. Anything painted over an object that
    // takes pointer events would swallow the click that selects it.
    const container = show([obstacle('lawn', 1)]);
    for (const decoration of container.querySelectorAll('[aria-hidden="true"]')) {
      expect(decoration.getAttribute('pointer-events')).toBe('none');
    }
  });

  it('draws surfaces under the things that stand on them', () => {
    // A lawn under a shed, not over it. Order is a property of the kind, not
    // of the order somebody happened to click.
    const container = show([obstacle('shed', 1), obstacle('lawn', 2), obstacle('house', 3)]);
    const order = [...container.querySelectorAll('.obstacle')].map((n) =>
      (n.getAttribute('class') ?? '').replace('obstacle obstacle--', ''),
    );
    expect(order.indexOf('lawn')).toBeLessThan(order.indexOf('shed'));
    expect(order.indexOf('lawn')).toBeLessThan(order.indexOf('house'));
  });

  it('names an object by what it is, texture or no texture', () => {
    // The texture is decoration and never the only thing carrying a meaning.
    show([obstacle('gravel', 1)]);
    expect(screen.getByRole('button', { name: /Kies/ })).toBeDefined();
  });
});
