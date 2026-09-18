import type { GardenOut } from '../api/client';
import type { Point } from '../canvas/viewport';
import { bed, box, disc, element, gardenOf, house, planting } from './build';

export { coloursFor } from './build';

/*
 * The contact sheet's three gardens (doc 95). Synthetic on purpose: a garden
 * imported from the map carries OSM's licence, and a fixture must not change
 * when the map does.
 */

export interface SheetGarden {
  id: string;
  /** What the sheet calls it. */
  title: string;
  garden: GardenOut;
  /** Where every zoom level is centred. */
  centre: Point;
}

/** June: most of what the sheet plants is in flower, and one is not. */
export const SHEET_MONTH = 6;

/** 10 × 20 m behind a terraced house: every kind there is, once at least. */
function small(): GardenOut {
  return gardenOf('Reihenhausgarten', [
    bed(501, 'Staudenbeet', [-4, 2.5], box(2, 9),
      [planting(1001, 1, 5), planting(1002, 2, 4), planting(1003, 3, 6), planting(1004, 4, 3)]),
    bed(502, 'Hochbeet', [-1, -5], box(3, 2),
      [planting(1005, 5, 4), planting(1006, 7, 3), planting(1007, 8, 2)],
      { height_above_ground: 0.4 }),
  ], [
    element(1, 'garden', [0, 0], box(10, 20)),
    house(2, [0, 14.5], 10, 9),
    element(3, 'street', [0, 22], box(24, 6)),
    element(4, 'paving', [0, 8.5], box(10, 3)),
    element(5, 'lawn', [0.75, 1.5], box(6.5, 9)),
    element(6, 'path', [0.3, -8.25], box(1, 3.5)),
    element(7, 'gravel', [3, -8.5], box(3, 2)),
    element(8, 'pond', [3, -5], disc(1.2)),
    element(9, 'shed', [-3.55, -8.8], box(2.5, 2)),
    element(10, 'tree', [3, 4], disc(2.5)),
    element(11, 'shrub', [-4, -4], disc(0.9)),
    element(12, 'hedge', [5.3, 0], box(0.6, 20)),
    element(13, 'fence', [-5.05, 0], box(0.1, 20)),
    element(14, 'wall', [0, -10.15], box(10, 0.3)),
    element(15, 'other', [4, 8.5], box(1, 1), { label: 'Grill' }),
  ]);
}

/** 60 × 40 m of farmyard: mostly surface, a barn, an orchard. */
function farmyard(): GardenOut {
  const trees = [[-27, -16], [-22, -16], [-17, -16], [-27, -10], [-22, -10], [-17, -10],
    [-27, -4], [-22, -4]].map(([x, y], i) => element(20 + i, 'tree', [x!, y!], disc(2.4)));
  const beds = [12, 15, 18, 21].map((x, i) =>
    bed(501 + i, `Gemüse ${i + 1}`, [x, -13], box(2, 6), [planting(1001 + i, [7, 3, 6, 5][i]!, 8)]));
  return gardenOf('Hof', beds, [
    element(1, 'garden', [0, 0], box(60, 40)),
    house(2, [-12, 12], 24, 12, 'gable', { height: 11, label: 'Scheune' }),
    element(3, 'shed', [14, 14], box(12, 8), { height: 4, label: 'Stall' }),
    element(4, 'shed', [22, -14], box(3, 3)),
    element(5, 'shed', [-24, 14.5], box(4, 3)),
    element(6, 'gravel', [0, 0], box(20, 12)),
    element(7, 'paving', [15, 2], box(10, 8)),
    element(8, 'lawn', [-21, -8], box(18, 24)),
    element(9, 'hedge', [0, -19.6], box(60, 0.8)),
    element(10, 'hedge', [29.6, 0], box(0.8, 40)),
    element(11, 'pond', [-4, -14], disc(3)),
    element(12, 'path', [10.5, -8], box(1, 4)),
    element(13, 'street', [0, 23], box(70, 6)),
    ...trees,
  ]);
}

/** A terraced block: two rows of houses, a street, ten backyards, one of them ours. */
function city(): GardenOut {
  const obstacles = [
    element(1, 'street', [0, 17], box(70, 6)),
    element(2, 'paving', [0, 13], box(70, 2)),
    element(3, 'paving', [0, 21], box(70, 2)),
    element(4, 'wall', [0, -13.15], box(60, 0.3)),
    element(5, 'gravel', [0, -14.15], box(60, 1.7)),
    element(6, 'garden', [-3, -5.5], box(6, 15)),
  ];
  let id = 10;
  const next = () => (id += 1);
  for (let i = 0; i < 10; i += 1) {
    const x = -27 + 6 * i;
    obstacles.push(house(next(), [x, 7], 6, 10), house(next(), [x, 27], 6, 10));
    obstacles.push(element(next(), 'tree', [x, 13], disc(1.5)));
    obstacles.push(element(next(), 'paving', [x, 0.75], box(6, 2.5)));
    obstacles.push(element(next(), 'shed', [x + 1.5, -11.5], box(2, 2)));
    obstacles.push(element(next(), 'tree', [x - 1, -9], disc(1.8)));
    if (i !== 4) {
      obstacles.push(element(next(), 'lawn', [x, -5], box(5, 7)));
      obstacles.push(element(next(), 'shrub', [x + 2, -3], disc(0.7)));
    }
    if (i % 3 === 0) obstacles.push(element(next(), 'other', [x - 2, -1.5], disc(0.4), { label: 'Regentonne' }));
  }
  for (let i = 0; i <= 10; i += 1) obstacles.push(element(next(), 'fence', [-30 + 6 * i, -5.5], box(0.1, 15)));
  return gardenOf('Blockinnenhof', [
    bed(501, 'Rabatte', [-5.2, -5], box(1.4, 9), [planting(1001, 4, 6), planting(1002, 2, 5)]),
    bed(502, 'Kräuter', [-1.5, -4], box(2, 2), [planting(1003, 1, 4)]),
    bed(503, 'Hochbeet', [-1.5, -7.5], box(2, 1.5), [planting(1004, 7, 3)], { height_above_ground: 0.5 }),
  ], obstacles);
}

export const SHEET_GARDENS: SheetGarden[] = [
  { id: 'small', title: 'Reihenhausgarten', garden: small(), centre: { x: 0, y: 2 } },
  { id: 'farmyard', title: 'Hof', garden: farmyard(), centre: { x: 8, y: -5 } },
  { id: 'city', title: 'Blockinnenhof', garden: city(), centre: { x: -3, y: -5 } },
];
