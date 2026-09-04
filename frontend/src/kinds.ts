/**
 * What a garden is made of, in German.
 *
 * The single list. It was three — the palette, the canvas labels and the object
 * editor each kept their own — and the editor's had already drifted: it still
 * offered "Gebäude", a kind the server stopped knowing when houses and sheds
 * became separate things. A dropdown that writes a kind the server rejects is
 * a form that fails on save, so the list lives here once.
 *
 * Mirrors `ninanatur/garden/objects.py::TRAITS`. A pytest guard fails if the two
 * fall out of step; the German words exist only here, because the server stores
 * the kind and never the word.
 */

export interface Kind {
  kind: string;
  label: string;
  /** The size it arrives at, said in the palette so nobody has to place one. */
  size: string;
  /** Starting height in metres; null for surfaces and for "Sonstiges", which
   *  claims nothing rather than inventing a number the user never gave. */
  height: number | null;
  /** Standing things cast shadows and draw on top; surfaces do neither. */
  standing: boolean;
  /** What the plan draws it as. Mirrors `KindTraits.symbol`. */
  symbol: string;
}

/** The one kind that holds plants. Mirrors `models.PLANTING_KIND`. */
export const PLANTING_KIND = 'bed';

export const KINDS: Kind[] = [
  { kind: 'house', label: 'Wohnhaus', size: '10 × 8 m', height: 6, standing: true, symbol: 'building' },
  { kind: 'shed', label: 'Schuppen', size: '3 × 2,5 m', height: 2.4, standing: true, symbol: 'building' },
  { kind: 'wall', label: 'Mauer', size: '6 × 0,3 m', height: 2, standing: true, symbol: 'masonry' },
  { kind: 'fence', label: 'Zaun', size: '6 × 0,1 m', height: 1.2, standing: true, symbol: 'fence' },
  { kind: 'hedge', label: 'Hecke', size: '6 × 0,6 m', height: 2, standing: true, symbol: 'foliage' },
  { kind: 'tree', label: 'Baum', size: '6 m Krone', height: 8, standing: true, symbol: 'crown' },
  { kind: 'shrub', label: 'Strauch', size: '2 m Krone', height: 1.5, standing: true, symbol: 'crown' },
  // The ground the rest sits on, drawn by the map import. Its own kind since
  // Wave 15: arriving as a flower bed made the whole plot one bed and left no
  // line between "my garden" and "a place I am planting".
  { kind: 'garden', label: 'Garten', size: '20 × 20 m', height: null, standing: false, symbol: 'plain' },
  { kind: 'bed', label: 'Blumenbeet', size: '3 × 1,5 m', height: null, standing: false, symbol: 'planting' },
  { kind: 'lawn', label: 'Rasen', size: '8 × 6 m', height: null, standing: false, symbol: 'grass' },
  { kind: 'paving', label: 'Pflaster', size: '4 × 3 m', height: null, standing: false, symbol: 'slabs' },
  { kind: 'gravel', label: 'Kies', size: '3 × 2 m', height: null, standing: false, symbol: 'stipple' },
  { kind: 'pond', label: 'Teich', size: '3 m', height: null, standing: false, symbol: 'water' },
  { kind: 'path', label: 'Weg', size: '6 × 1 m', height: null, standing: false, symbol: 'slabs' },
  { kind: 'street', label: 'Straße', size: '20 × 6 m', height: null, standing: false, symbol: 'tarmac' },
  { kind: 'other', label: 'Sonstiges', size: '2 × 2 m', height: null, standing: true, symbol: 'plain' },
];

export const STANDING = KINDS.filter((k) => k.standing && k.kind !== 'other');
export const SURFACES = KINDS.filter((k) => !k.standing);

const BY_KIND = new Map(KINDS.map((k) => [k.kind, k]));

/** The German word, falling back to the raw kind rather than to nothing: an
 *  object the server knows and we do not should still be readable on the plan. */
export function labelOf(kind: string): string {
  return BY_KIND.get(kind)?.label ?? kind;
}

export function heightOf(kind: string): number | null {
  return BY_KIND.get(kind)?.height ?? null;
}

/**
 * The ground itself. It is not moved, resized or dragged.
 *
 * The map import draws it and it is where everything else is measured from —
 * shifting it would move the garden out from under the plan rather than move
 * anything in it. The gardener said as much: not being able to drag it is the
 * behaviour they liked, and it survived Wave 15 only because it was noticed.
 * Before, it held by accident: the outline was a bed, and beds happened to be
 * unmovable because selection could not find them.
 */
export const GROUND_KIND = 'garden';

export function isGround(kind: string): boolean {
  return kind === GROUND_KIND;
}
