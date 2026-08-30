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
}

export const KINDS: Kind[] = [
  { kind: 'house', label: 'Wohnhaus', size: '10 × 8 m', height: 6, standing: true },
  { kind: 'shed', label: 'Schuppen', size: '3 × 2,5 m', height: 2.4, standing: true },
  { kind: 'wall', label: 'Mauer', size: '6 × 0,3 m', height: 2, standing: true },
  { kind: 'fence', label: 'Zaun', size: '6 × 0,1 m', height: 1.2, standing: true },
  { kind: 'hedge', label: 'Hecke', size: '6 × 0,6 m', height: 2, standing: true },
  { kind: 'tree', label: 'Eiche', size: '6 m Krone', height: 8, standing: true },
  { kind: 'shrub', label: 'Nussstrauch', size: '2 m Krone', height: 1.5, standing: true },
  { kind: 'bed', label: 'Blumenbeet', size: '3 × 1,5 m', height: null, standing: false },
  { kind: 'lawn', label: 'Rasen', size: '8 × 6 m', height: null, standing: false },
  { kind: 'paving', label: 'Pflaster', size: '4 × 3 m', height: null, standing: false },
  { kind: 'gravel', label: 'Kies', size: '3 × 2 m', height: null, standing: false },
  { kind: 'pond', label: 'Teich', size: '3 m', height: null, standing: false },
  { kind: 'path', label: 'Weg', size: '6 × 1 m', height: null, standing: false },
  { kind: 'other', label: 'Sonstiges', size: '2 × 2 m', height: null, standing: true },
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
