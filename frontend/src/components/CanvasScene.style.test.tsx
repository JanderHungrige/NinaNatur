import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GardenOut } from '../api/client';
import { KINDS } from '../kinds';
import { clustersFor } from '../canvas/clusters';
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
    points: null,
    constraint_hint: null,
    height: 2,
    label: null,
    roof: 'unknown',
    height_source: 'user',
    footprint: [[-2, 1.5], [2, 1.5], [2, -1.5], [-2, -1.5]],
  };
}

function garden(obstacles: GardenOut['obstacles']): GardenOut {
  return {
    unidentified_plantings: 0, soil_type: null, moisture: null, observed_colours: {},
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
    for (const name of [/Teich/, /Baum/]) {
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

  it('does not read out a height that does not exist', () => {
    // The server stopped inventing 0.0 for a pond; the label went on reading it
    // out, so the plan announced "Teich, null m hoch".
    show([{ ...obstacle('pond', 1), height: null }]);

    const node = screen.getByRole('button', { name: /Teich/ });
    expect(node.getAttribute('aria-label')).toBe('Teich');
  });

  it('names an object by what it is, texture or no texture', () => {
    // The texture is decoration and never the only thing carrying a meaning.
    show([obstacle('gravel', 1)]);
    expect(screen.getByRole('button', { name: /Kies/ })).toBeDefined();
  });
});

describe('CanvasScene — what lies on top of what', () => {
  it('does not bury a drawn element under a bed', () => {
    // A bed used to be drawn after every object, so anything drawn on top of
    // one was unreachable: the click landed on the bed. Reported from the
    // running app, where it makes new shapes look unselectable.
    const container = render(
      <GardenCanvas
        garden={{
          ...garden([obstacle('other', 1)]),
          beds: [
            {
              bed_id: 9, name: 'Gesamtfläche',
              // Wave 15: a bed carries the same geometry an obstacle does.
              kind: 'bed',
              shape: 'polygon',
              x: 0,
              y: 0,
              points: null,
              width: null,
              constraint_hint: null,
              polygon: [[-20, -20], [20, -20], [20, 20], [-20, 20]],
              soil_type: 'loam', moisture: 'fresh',
              ellenberg_l: null, ellenberg_m: null, ellenberg_n: null,
              ellenberg_r: null, sun_hours: null, slope_deg: null, aspect_deg: null, light_computed_at: null,
              height_above_ground: 0, label: null, plantings: [],
            },
          ],
        }}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }}
        onSelectObstacle={vi.fn()}
      />,
    ).container;

    const drawn = [...container.querySelectorAll('.bed, .obstacle')].map((n) =>
      n.classList.contains('bed') ? 'bed' : 'obstacle',
    );
    // Later in document order is nearer the front in SVG.
    expect(drawn.lastIndexOf('bed')).toBeLessThan(drawn.lastIndexOf('obstacle'));
  });

  it('still keeps surfaces under the things standing on them', () => {
    const container = render(
      <GardenCanvas
        garden={garden([obstacle('shed', 1), obstacle('lawn', 2)])}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }}
        onSelectObstacle={vi.fn()}
      />,
    ).container;
    const order = [...container.querySelectorAll('.obstacle')].map((n) =>
      (n.getAttribute('class') ?? '').replace('obstacle obstacle--', ''),
    );
    expect(order.indexOf('lawn')).toBeLessThan(order.indexOf('shed'));
  });
});

describe('CanvasScene — big things behind, small things in front', () => {
  function plan(obstacles: GardenOut['obstacles'], beds: GardenOut['beds']) {
    return render(
      <GardenCanvas
        garden={{ ...garden(obstacles), beds }}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }}
        onSelectObstacle={vi.fn()}
      />,
    ).container;
  }

  const wholeGarden: GardenOut['beds'][number] = {
    bed_id: 9, name: 'Gesamtfläche',
    // Wave 15: a bed carries the same geometry an obstacle does.
    kind: 'bed',
    shape: 'polygon',
    x: 0,
    y: 0,
    points: null,
    width: null,
    constraint_hint: null,
    polygon: [[-20, -20], [20, -20], [20, 20], [-20, 20]],
    soil_type: 'loam', moisture: 'fresh', ellenberg_l: null, ellenberg_m: null,
    ellenberg_n: null, ellenberg_r: null, sun_hours: null, slope_deg: null, aspect_deg: null,
    light_computed_at: null, height_above_ground: 0, label: null, plantings: [],
  };

  it('keeps the garden-wide bed behind a surface drawn on it', () => {
    // Both are surfaces, so they ranked equal and the stable sort put beds
    // last — which is in front. A gravel path inside the garden outline was
    // buried under it.
    const container = plan([obstacle('gravel', 1)], [wholeGarden]);
    const order = [...container.querySelectorAll('.bed, .obstacle')].map((n) =>
      n.classList.contains('bed') ? 'bed' : 'obstacle',
    );
    expect(order.indexOf('bed')).toBeLessThan(order.indexOf('obstacle'));
  });

  it('keeps a small bed in front of a big lawn', () => {
    // The rule is size, not kind: a bed drawn on a lawn is meant to be seen.
    const lawn = { ...obstacle('lawn', 1) };
    lawn.footprint = [[-15, -15], [15, -15], [15, 15], [-15, 15]];
    const container = plan([lawn], [{
      ...wholeGarden, bed_id: 3, name: 'Staudenbeet',
      polygon: [[0, 0], [3, 0], [3, 2], [0, 2]],
    }]);
    const order = [...container.querySelectorAll('.bed, .obstacle')].map((n) =>
      n.classList.contains('bed') ? 'bed' : 'obstacle',
    );
    expect(order.indexOf('obstacle')).toBeLessThan(order.indexOf('bed'));
  });

  it('still keeps everything standing in front of every surface', () => {
    // A shed on a lawn, however small the lawn.
    const shed = obstacle('shed', 2);
    shed.footprint = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
    const container = plan([shed, obstacle('lawn', 1)], []);
    const order = [...container.querySelectorAll('.obstacle')].map((n) =>
      (n.getAttribute('class') ?? '').replace('obstacle obstacle--', ''),
    );
    expect(order.indexOf('lawn')).toBeLessThan(order.indexOf('shed'));
  });
});

describe('CanvasScene — plantings as patches', () => {
  const outline = [[0, 0], [8, 0], [8, 6], [0, 6]];

  function patches(clusters: Parameters<typeof clustersFor>[1], month: number | null) {
    const colours = clusters.map((c) => ({
      planting_id: c.planting_id,
      colour: 'yellow',
      months: [6],
      space_m2: null,
    }));
    return render(
      <GardenCanvas
        garden={garden([])}
        selectedBedId={null}
        onSelectBed={vi.fn()}
        size={{ widthPx: 800, heightPx: 600 }}
        clusters={clustersFor(outline, clusters, colours, month)}
      />,
    ).container;
  }

  function planting(id: number, quantity = 6) {
    return {
      planting_id: id, taxon_id: 7, canonical_name: 'Salvia pratensis',
      raw_name: null, quantity, x: null, y: null,
    };
  }

  it('draws a patch of dots per planting rather than a bar across the bed', () => {
    const container = patches([planting(1)], 6);
    expect(container.querySelectorAll('.bloom-dot').length).toBeGreaterThan(4);
    // The bed keeps its own fill: the plants are drawn on top of it.
    const bed = container.querySelector('.bed') as SVGElement | null;
    expect(bed?.style.fill ?? '').toBe('');
  });

  it('draws a planting that is not in flower, in grey', () => {
    // The reported bug, and the reason the hatch had to go. A bed whose
    // colours were all unrecorded used to be filled with a striped pattern —
    // "Farbstreifen", exactly as described — and a bed out of season showed
    // nothing at all, so an empty bed and a bed full of leaves looked alike.
    const container = patches([planting(1)], 1);

    const dots = container.querySelectorAll('.bloom-dot');
    expect(dots.length).toBeGreaterThan(0);
    expect(dots[0]!.getAttribute('fill')).toBe('var(--ink-muted)');
  });

  it('never paints a band or a hatch across a bed again', () => {
    const container = patches([planting(1)], 1);
    expect(container.querySelector('#bloom-unknown')).toBeNull();
    for (const bed of container.querySelectorAll('.bed')) {
      expect((bed as SVGElement).style.fill).not.toContain('url(');
    }
  });

  it('keeps each species in its own patch', () => {
    // Nobody plants one salvia here and one over there. Scattering a species
    // evenly across the bed says something untrue about the garden.
    const container = patches([planting(1), planting(2)], 6);
    expect(container.querySelectorAll('.cluster')).toHaveLength(2);
  });

  it('draws nothing for a bed with nothing in it', () => {
    const container = patches([], 6);
    expect(container.querySelectorAll('.bloom-dot')).toHaveLength(0);
  });
});

// The tests for pigment, a pooled rim and large scattered tiles stood here.
// The painted look was reverted at the user's request: it did not work, and
// tuning it further was not worth the time it would take. What was learnt is
// written down in .mdd/docs/58-painted-plan.md rather than lost — a tile small
// enough to hold one mark can only repeat into a grid, a wobble under half a
// metre is invisible across a garden, and desaturated noise multiplied over a
// wash is dirt rather than paint.

