import { describe, expect, it } from 'vitest';

import { bed, garden, planting, richGarden, shed } from '../testing/gardens';
import { formValues, resolveSelection, selectedIds, viewKey } from './selection';

describe('resolveSelection — what the pick is, in this garden', () => {
  it('is the garden when nothing is picked', () => {
    expect(resolveSelection(richGarden(), null)).toEqual({ kind: 'none' });
  });

  it('is the bed when the picked element is a bed', () => {
    const g = richGarden();
    expect(resolveSelection(g, { what: 'element', id: 1 })).toEqual({ kind: 'bed', bed: g.beds[0] });
  });

  it('is the element when the picked element is not a bed', () => {
    const g = richGarden();
    expect(resolveSelection(g, { what: 'element', id: 5 })).toEqual({
      kind: 'element',
      element: g.obstacles[0],
    });
  });

  it('is the patch, together with the bed that holds it', () => {
    const g = richGarden();
    expect(resolveSelection(g, { what: 'planting', id: 11 })).toEqual({
      kind: 'planting',
      planting: g.beds[0]!.plantings[0],
      bed: g.beds[0],
    });
  });

  it('is nothing once the picked thing has gone', () => {
    // Deleted, or taken back with undo. A selection of something that is not
    // there would be a panel about nothing.
    expect(resolveSelection(richGarden({ obstacles: [] }), { what: 'element', id: 5 })).toEqual({
      kind: 'none',
    });
    expect(resolveSelection(garden('tok', 'Testgarten'), { what: 'planting', id: 11 })).toEqual({
      kind: 'none',
    });
  });

  it('follows an element that became a bed, without it being picked again', () => {
    // Draw first, say what it is afterwards: a shape called Blumenbeet moves
    // from `obstacles` to `beds` in the server's answer, under the same id.
    const asBed = bed({ bed_id: 5, name: 'Beet 2', label: 'Gartenhaus' });
    const g = richGarden({ beds: [bed(), asBed], obstacles: [] });
    expect(resolveSelection(g, { what: 'element', id: 5 })).toEqual({ kind: 'bed', bed: asBed });
  });
});

describe('selectedIds — one answer for the plan', () => {
  it('gives a bed its planting site and its handles, and no patch', () => {
    const selection = resolveSelection(richGarden(), { what: 'element', id: 1 });
    expect(selectedIds(selection)).toEqual({ bedId: 1, elementId: 1, plantingId: null });
  });

  it('gives an element its handles and nothing else', () => {
    const selection = resolveSelection(richGarden(), { what: 'element', id: 5 });
    expect(selectedIds(selection)).toEqual({ bedId: null, elementId: 5, plantingId: null });
  });

  it('gives a patch itself and nothing else — not the bed it stands in', () => {
    const selection = resolveSelection(richGarden(), { what: 'planting', id: 11 });
    expect(selectedIds(selection)).toEqual({ bedId: null, elementId: null, plantingId: 11 });
  });

  it('gives nothing for nothing', () => {
    expect(selectedIds({ kind: 'none' })).toEqual({ bedId: null, elementId: null, plantingId: null });
  });
});

describe('viewKey — which view the details are showing', () => {
  it('tells every view apart', () => {
    const g = richGarden();
    const keys = [
      viewKey({ kind: 'none' }),
      viewKey(resolveSelection(g, { what: 'element', id: 1 })),
      viewKey(resolveSelection(g, { what: 'element', id: 5 })),
      viewKey(resolveSelection(g, { what: 'planting', id: 11 })),
    ];
    expect(new Set(keys).size).toBe(4);
  });

  it('tells an element from the bed it has just become', () => {
    // Same id, a different view: the focus has to know the view changed.
    expect(viewKey({ kind: 'element', element: shed() })).not.toBe(
      viewKey({ kind: 'bed', bed: bed({ bed_id: 5 }) }),
    );
  });
});

describe('formValues — where the element form starts', () => {
  it('reads a bed: what stands in it, how high it is raised, its own soil', () => {
    const raised = bed({
      plantings: [planting()],
      height_above_ground: 0.4,
      soil_type: 'sand',
      moisture: 'dry',
      label: 'Hochbeet',
    });
    expect(formValues(raised)).toEqual({
      kind: 'bed', label: 'Hochbeet', plantings: 1, shape: 'polygon', roof: 'unknown',
      roofSource: 'user', roofFallDeg: null, roofPitchDeg: null, eavesM: null, eavesSource: null,
      height: null, width: null,
      soilType: 'sand', moisture: 'dry', heightAboveGround: 0.4,
    });
  });

  it('reads an element: its height, its roof and its eaves', () => {
    expect(formValues(shed({ roof: 'gable', eaves_m: 1.9 }))).toEqual({
      kind: 'shed', label: 'Gartenhaus', plantings: 0, shape: 'polygon', roof: 'gable',
      roofSource: 'user', roofFallDeg: null, roofPitchDeg: null, eavesM: 1.9, eavesSource: null,
      height: 2.4, width: null,
      soilType: null, moisture: null, heightAboveGround: 0,
    });
  });

  it('reads where the roof and the eaves came from (doc 93)', () => {
    const values = formValues(shed({ roof_source: 'surveyed', eaves_m: 1.9, eaves_source: 'surveyed' }));
    expect(values.roofSource).toBe('surveyed');
    expect(values.eavesSource).toBe('surveyed');
  });

  it('reads which way the roof falls and the pitch the model uses (doc 94)', () => {
    const values = formValues(shed({ roof: 'pent', roof_fall_deg: 180, roof_pitch_deg: 11.3 }));
    expect(values.roofFallDeg).toBe(180);
    expect(values.roofPitchDeg).toBe(11.3);
  });
});
