import type { GardenOut } from '../api/client';
import { bed, box, disc, element, gardenOf, house, lineElement, planting } from './build';
import type { SheetGarden } from './gardens';

/*
 * The fourth garden (doc 98): what a theme draws that the first three do not
 * show — every roof the model knows, a raised bed beside a flat one, a hedge
 * and a fence drawn as lines, a wall, shrubs among trees, two streets meeting.
 * Drawn for themes other than Technisch only: Technisch's record is of the
 * three it was taken with, and a garden added to it would be a record changed.
 */

function vocabulary(): GardenOut {
  return gardenOf('Musterblatt', [
    bed(501, 'Hochbeet', [5, -1], box(3, 1.5),
      [planting(1001, 1, 4), planting(1002, 7, 3)], { height_above_ground: 0.5 }),
    bed(502, 'Staudenbeet', [5, -4.2], box(4, 1.5),
      [planting(1003, 4, 5), planting(1004, 2, 4), planting(1005, 8, 2)]),
  ], [
    element(1, 'garden', [0, 0], box(30, 22)),
    // Two ways meeting, as the map sends them: one band over another (doc 98).
    lineElement(18, 'street', [-18, 13.5], [18, 13.5], 6),
    lineElement(19, 'street', [6, 13.5], [6, 21], 5),
    house(2, [-9.5, 6.5], 9, 6),
    house(3, [0.5, 6.5], 8, 6, 'hip'),
    house(4, [9, 7], 5, 4, 'pent', { roof_fall_deg: 180, height: 5, eaves_m: 3 }),
    house(5, [12, -1.5], 4, 5, 'flat', { height: 3 }),
    element(6, 'lawn', [-6, -3], box(12, 8)),
    element(7, 'paving', [-9.5, 2], box(9, 2)),
    element(8, 'path', [2.2, 1.2], box(1, 4.5)),
    element(9, 'pond', [-3.5, -4], disc(1.3)),
    element(10, 'gravel', [9.5, -6.5], box(4, 2)),
    lineElement(11, 'hedge', [-14, -9.3], [6, -9.3], 0.8),
    lineElement(12, 'fence', [14.5, -10.5], [14.5, 4], 0.1),
    element(13, 'wall', [9, -8.8], box(8, 0.3)),
    element(14, 'tree', [-11.5, -4], disc(2.2)),
    element(15, 'shrub', [-1.2, 0.2], disc(0.9)),
    element(16, 'shrub', [0.8, -6], disc(1.1)),
    element(17, 'shrub', [9, -3.2], disc(0.7)),
  ]);
}

export const THEME_GARDENS: SheetGarden[] = [
  { id: 'vocabulary', title: 'Musterblatt', garden: vocabulary(), centre: { x: 0, y: -1 } },
];
