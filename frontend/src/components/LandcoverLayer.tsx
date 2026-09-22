import { memo, useId, useMemo } from 'react';

import type { GardenOut, Landcover } from '../api/client';
import { landPaths, outsidePlots, plotsOf } from '../canvas/landcover';
import type { PlanTheme } from '../themes/types';
import { LandcoverAreas } from './LandcoverAreas';

interface Props {
  landcover: Landcover;
  /** The garden's elements, for its plot: the one thing the land is cut out of. */
  obstacles: GardenOut['obstacles'];
  theme: PlanTheme;
  /** The plan's scale in halvings (`planScale`), never the view itself. */
  scale: number;
}

/**
 * The land around the garden, from OpenStreetMap (doc 114): woods, fields,
 * water, parks, houses, under everything the gardener drew.
 *
 * Context, not content. Faint, without an outline, never a target and never
 * read out; streets and houses are elements drawn over it. The plot is cut out
 * of every class — OpenStreetMap nearly always calls a private garden
 * "residential", and the plot keeps its own ground.
 *
 * Cut with a clip, not a mask: a mask is an offscreen image painted again on
 * every frame of a pan, a clip is one more path. Memoised on the data, the
 * theme and the scale, so a pan never draws it again (doc 113).
 */
function Landcover({ landcover, obstacles, theme, scale }: Props) {
  const id = `landcover-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const paths = useMemo(() => landPaths(landcover), [landcover]);
  const outside = useMemo(() => outsidePlots(landcover, plotsOf(obstacles)), [landcover, obstacles]);
  if (paths.length === 0) return null;
  return (
    <>
      {outside !== null && (
        <defs>
          <clipPath id={id}>
            <path d={outside} clipRule="evenodd" />
          </clipPath>
        </defs>
      )}
      <g className="landcover" data-testid="landcover" aria-hidden="true"
         clipPath={outside === null ? undefined : `url(#${id})`}>
        <LandcoverAreas paths={paths} theme={theme} lod={theme.lodAt(scale)} />
      </g>
    </>
  );
}

export const LandcoverLayer = memo(Landcover);
