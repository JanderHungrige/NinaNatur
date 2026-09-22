import type { LandKind, LandPath } from '../canvas/landcover';
import type { LevelOfDetail, PlanTheme } from '../themes/types';

/**
 * The symbol a class of land is painted with, from the theme's own vocabulary
 * (doc 114), so both themes draw it without a line of theme code: a wood is a
 * hedge's foliage, a car park the street's tarmac. Fields and houses have no
 * symbol that fits; the stylesheet gives them flat washes (`.landcover__area--*`).
 */
const SYMBOL: Readonly<Partial<Record<LandKind, string>>> = {
  grass: 'grass',
  wood: 'foliage',
  water: 'water',
  paved: 'tarmac',
  built: 'tarmac',
  allotments: 'planting',
};

interface Props {
  paths: readonly LandPath[];
  theme: PlanTheme;
  lod: LevelOfDetail;
}

/** One path per class of land, in the order given. */
export function LandcoverAreas({ paths, theme, lod }: Props) {
  return (
    <>
      {paths.map(({ kind, d }) => {
        const symbol = SYMBOL[kind];
        return (
          <path key={kind} d={d} fillRule="nonzero"
                className={`landcover__area landcover__area--${kind}`}
                fill={symbol === undefined ? undefined : theme.fill(symbol, lod)} />
        );
      })}
    </>
  );
}
