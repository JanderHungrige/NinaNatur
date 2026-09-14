import type { GardenOut } from '../api/client';

type Bed = GardenOut['beds'][number];
type Obstacle = GardenOut['obstacles'][number];
type Planting = Bed['plantings'][number];

/** What was picked: an element — a bed is one — or a patch of plants. */
export type Picked = { what: 'element'; id: number } | { what: 'planting'; id: number } | null;

/** What the pick is, in this garden (doc 88). */
export type Selection =
  | { kind: 'none' }
  | { kind: 'bed'; bed: Bed }
  | { kind: 'element'; element: Obstacle }
  | { kind: 'planting'; planting: Planting; bed: Bed };

/** The ids the plan draws a selection with. */
export interface SelectedIds {
  /** The bed selected for planting. */
  bedId: number | null;
  /** The bed or element wearing handles. */
  elementId: number | null;
  plantingId: number | null;
}

/** Where the element form starts: what the element already is. */
export interface FormValues {
  kind: string;
  label: string | null;
  /** How many plants stand in it, for the warning before they go with it. */
  plantings: number;
  /** 'polygon' | 'circle' | 'line'. Only a line has a width to set. */
  shape: string;
  roof: string;
  /** Where the roof starts. Null is "nobody has said". */
  eavesM: number | null;
  height: number | null;
  width: number | null;
  soilType: string | null;
  moisture: string | null;
  heightAboveGround: number;
}

const NOTHING: Selection = { kind: 'none' };

/**
 * What the pick is, read from the garden every time (doc 88).
 *
 * The pick is only an id. Reading it against the garden on every render is what
 * keeps an element called Blumenbeet — moved from `obstacles` to `beds` by the
 * server — selected as the bed it has become, and what makes something deleted
 * or undone simply no longer selected.
 */
export function resolveSelection(garden: GardenOut, picked: Picked): Selection {
  if (picked === null) return NOTHING;
  if (picked.what === 'element') {
    const bed = garden.beds.find((b) => b.bed_id === picked.id);
    if (bed !== undefined) return { kind: 'bed', bed };
    const element = garden.obstacles.find((o) => o.obstacle_id === picked.id);
    return element === undefined ? NOTHING : { kind: 'element', element };
  }
  for (const bed of garden.beds) {
    const planting = bed.plantings.find((p) => p.planting_id === picked.id);
    if (planting !== undefined) return { kind: 'planting', planting, bed };
  }
  return NOTHING;
}

/**
 * One answer for the plan. A bed is selected for planting and wears its handles;
 * an element only wears handles; a patch is only itself, not the bed it stands in.
 */
export function selectedIds(selection: Selection): SelectedIds {
  switch (selection.kind) {
    case 'bed':
      return { bedId: selection.bed.bed_id, elementId: selection.bed.bed_id, plantingId: null };
    case 'element':
      return { bedId: null, elementId: selection.element.obstacle_id, plantingId: null };
    case 'planting':
      return { bedId: null, elementId: null, plantingId: selection.planting.planting_id };
    default:
      return { bedId: null, elementId: null, plantingId: null };
  }
}

/** Which view the details show. A bed and the element it was a moment ago are two views. */
export function viewKey(selection: Selection): string {
  switch (selection.kind) {
    case 'bed':
      return `bed-${selection.bed.bed_id}`;
    case 'element':
      return `element-${selection.element.obstacle_id}`;
    case 'planting':
      return `planting-${selection.planting.planting_id}`;
    default:
      return 'none';
  }
}

/** The element form's starting values. Only a bed has its own soil and a raised
 *  height; only an element has a height, a roof and eaves. */
export function formValues(item: Bed | Obstacle): FormValues {
  if ('bed_id' in item) {
    return {
      kind: item.kind,
      label: item.label,
      plantings: item.plantings.length,
      shape: item.shape,
      roof: 'unknown',
      eavesM: null,
      height: null,
      width: item.width,
      soilType: item.soil_type,
      moisture: item.moisture,
      heightAboveGround: item.height_above_ground,
    };
  }
  return {
    kind: item.kind,
    label: item.label,
    plantings: 0,
    shape: item.shape,
    roof: item.roof,
    eavesM: item.eaves_m,
    height: item.height,
    width: item.width,
    soilType: null,
    moisture: null,
    heightAboveGround: 0,
  };
}
