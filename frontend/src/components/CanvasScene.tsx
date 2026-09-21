import { useMemo } from 'react';

import type { CanopySuggestion, GardenOut, LightMap, Terrain } from '../api/client';
import type { Cluster } from '../canvas/clusters';
import { type Point, type Viewport, svgPoints } from '../canvas/viewport';
import { usePlanTheme } from '../themes/context';
import { planScale } from './PlanDecorations';
import { ReliefMap } from './ReliefMap';
import { SceneWorld } from './SceneWorld';
import type { MapMode } from './SunMap';

/** One empty list for every render: a fresh `[]` default is a new prop each time,
 *  and the memoised world would be rebuilt for it. */
const NONE: never[] = [];

interface Props {
  garden: GardenOut;
  view: Viewport;
  spacing: number;
  selectedBedId: number | null;
  draft: Point[];
  viewpoint?: { x: number; y: number } | null;
  onSelectBed: (bedId: number) => void;
  onSelectObstacle?: ((obstacleId: number) => void) | undefined;
  /** The element selected, said on the plan as the selected bed is (doc 88). */
  selectedObstacleId?: number | null;
  /** A drawing tool is armed: the plan takes the click, not what is under it.
   *  Without this the first click to draw selects the garden-wide bed and the
   *  page scrolls away to the suggestions, so the tool looks like it needs two
   *  attempts.
   *
   *  The handlers are left off entirely rather than covered with
   *  `pointer-events: none`: not attaching is a guarantee, and a CSS property
   *  is a hope that nothing else ever sets it back. */
  armed?: boolean;
  /** Right-click, or the keyboard's context-menu key, on an element. */
  onAskWhatItIs?:
    | ((id: number, at: { x: number; y: number }) => void)
    | undefined;
  /** Grabbing a shape's body: a move, not a pan. */
  onGrabElement?: ((id: number, event: React.PointerEvent) => void) | undefined;
  /** Where the element being dragged is shown while the pointer holds it. */
  dragOffset?: { id: number; dx: number; dy: number } | null;
  /** Colours in flower per bed for the month being shown, if any. */
  /** Every planting in the garden as a patch, already positioned and coloured
   *  for the month being shown. */
  clusters?: Cluster[] | undefined;
  selectedPlantingId?: number | null;
  freshPlantingId?: number | null;
  onSelectCluster?: ((plantingId: number) => void) | undefined;
  onGrabCluster?: ((plantingId: number, event: React.PointerEvent) => void) | undefined;
  onShowClusterInfo?: ((taxonId: number, name: string) => void) | undefined;
  /** The sun map, when the switch is on. Drawn under the plantings and over the
   *  ground: it is about the ground, and it must not hide what grows on it. */
  sunMap?: { map: LightMap; mode: MapMode } | undefined;
  /** The ground itself, when it has been fetched. Drawn beneath the plan. */
  terrain?: Terrain | null | undefined;
  /** One frame of a day's shadows, while the day is being played. */
  shadows?: number[][][] | undefined;
  /** Trees the surface model found, marked where they stand (doc 89). */
  canopies?: CanopySuggestion[] | undefined;
}

/**
 * Everything inside the plan, as pure output.
 *
 * Split from GardenCanvas so the stateful half stays readable: this file knows
 * how the garden looks, that one knows what the pointer is doing. How the shapes
 * are painted is the theme's (doc 96): its defs, its fills and its one filter.
 */
export function CanvasScene({
  garden,
  view,
  spacing,
  selectedBedId,
  draft,
  viewpoint = null,
  onSelectBed,
  onSelectObstacle,
  selectedObstacleId = null,
  clusters = NONE,
  selectedPlantingId = null,
  freshPlantingId = null,
  onSelectCluster,
  onGrabCluster,
  onShowClusterInfo,
  sunMap,
  terrain,
  shadows,
  canopies = NONE,
  armed = false,
  onAskWhatItIs,
  onGrabElement,
  dragOffset = null,
}: Props) {
  const theme = usePlanTheme();
  const metresPerPixel = view.spanM / view.widthPx;
  const scale = planScale(metresPerPixel);
  // The same element while the theme and the scale are: Draft Sketch's defs are
  // seventy-odd patterns, and React skips an element it has already drawn.
  const defs = useMemo(() => <theme.Defs metresPerPixel={scale} />, [theme, scale]);

  return (
    <g className={`plan-theme plan-theme--${theme.id}`}>
        <defs>
          {defs}
          <pattern
            id="grid"
            width={spacing}
            height={spacing}
            patternUnits="userSpaceOnUse"
          >
            {/* 3 cm, or a pixel once 3 cm is more: in metres alone it was a
                13-pixel bar at the closest zoom (the owner's check, #1). */}
            <path d={`M ${spacing} 0 L 0 0 0 ${spacing}`} className="grid-line"
                  style={{ strokeWidth: Math.min(0.03, scale) }} />
          </pattern>
        </defs>
        {/* The sheet the plan is drawn on, where the theme brings one: under
            the grid, because the grid is drawn on the paper (doc 99). */}
        {theme.paper !== undefined && (
          <rect className="canvas__paper" aria-hidden="true"
                x={view.centreX - view.spanM} y={-view.centreY - view.spanM}
                width={view.spanM * 2} height={view.spanM * 2} fill={theme.paper} />
        )}
        <rect
          x={view.centreX - view.spanM}
          y={-view.centreY - view.spanM}
          width={view.spanM * 2}
          height={view.spanM * 2}
          fill="url(#grid)"
        />

        {/* Under everything, because it is what everything stands on. Faint
            enough to be invisible while somebody places a bed, and there when
            they look for it. */}
        {terrain !== undefined && terrain !== null && <ReliefMap terrain={terrain} />}

        {/* North marker — the whole light calculation hinges on which way is up. */}
        <text
          className="compass"
          x={view.centreX}
          y={-view.centreY - view.spanM * 0.35}
          textAnchor="middle"
        >
          N ↑
        </text>

        {/* Everything that does not move with the view, memoised (#11): a pan
            redraws what is above and below this, never what is in it. */}
        <SceneWorld
          garden={garden} scale={scale} spacing={spacing} selectedBedId={selectedBedId}
          selectedObstacleId={selectedObstacleId} viewpoint={viewpoint}
          onSelectBed={onSelectBed} onSelectObstacle={onSelectObstacle} armed={armed}
          onAskWhatItIs={onAskWhatItIs} onGrabElement={onGrabElement} dragOffset={dragOffset}
          clusters={clusters} selectedPlantingId={selectedPlantingId}
          freshPlantingId={freshPlantingId} onSelectCluster={onSelectCluster}
          onGrabCluster={onGrabCluster} onShowClusterInfo={onShowClusterInfo}
          sunMap={sunMap?.map} mapMode={sunMap?.mode} shadows={shadows} canopies={canopies}
        />

      {draft.length > 0 && (
          <g data-testid="draft" className="draft">
            <polyline points={svgPoints(draft)} className="draft__line" />
            {draft.map((p) => (
              <circle key={`${p.x},${p.y}`} cx={p.x} cy={-p.y} r={3.5 * metresPerPixel} />
            ))}
          </g>
        )}
    </g>
  );
}
