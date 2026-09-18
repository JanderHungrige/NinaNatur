import type { CanopySuggestion, GardenOut, LightMap, Terrain } from '../api/client';
import type { Cluster } from '../canvas/clusters';
import { type Point, type Viewport, svgPoints } from '../canvas/viewport';
import { usePlanTheme } from '../themes/context';
import { CanopyMarks } from './CanopyMarks';
import { ClusterLayer } from './ClusterLayer';
import { PlanObjects } from './PlanObjects';
import { ReliefMap } from './ReliefMap';
import { type MapMode, SunMap } from './SunMap';

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
  clusters = [],
  selectedPlantingId = null,
  freshPlantingId = null,
  onSelectCluster,
  onGrabCluster,
  onShowClusterInfo,
  sunMap,
  terrain,
  shadows,
  canopies = [],
  armed = false,
  onAskWhatItIs,
  onGrabElement,
  dragOffset = null,
}: Props) {
  const theme = usePlanTheme();
  const lod = theme.lodAt(view.spanM / view.widthPx);
  /** Shown where the pointer has it, saved where it is let go. */
  const shift = (id: number): string =>
    dragOffset !== null && dragOffset.id === id
      ? `translate(${dragOffset.dx} ${-dragOffset.dy})`
      : '';

  return (
    <g className={`plan-theme plan-theme--${theme.id}`}>
        <defs>
        <theme.Defs />
          <pattern
            id="grid"
            width={spacing}
            height={spacing}
            patternUnits="userSpaceOnUse"
          >
            <path d={`M ${spacing} 0 L 0 0 0 ${spacing}`} className="grid-line" />
          </pattern>
        </defs>
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

        <PlanObjects garden={garden} theme={theme} lod={lod} selectedBedId={selectedBedId}
                     selectedObstacleId={selectedObstacleId} armed={armed}
                     onSelectBed={onSelectBed} onSelectObstacle={onSelectObstacle}
                     onAskWhatItIs={onAskWhatItIs} onGrabElement={onGrabElement} shift={shift} />

        {sunMap !== undefined && (
          <SunMap map={sunMap.map} mode={sunMap.mode} />
        )}

        {/* Found trees where they stand (doc 89): a mark over the plan, never a target. */}
        <CanopyMarks trees={canopies} />

        {/* One moment of one day, over everything: while it plays, where the
            shadow is *now* is the only question being asked. */}
        {shadows !== undefined && (
          <g className="day-shadows" aria-hidden="true" pointerEvents="none">
            {shadows.map((polygon, i) => (
              <polygon
                key={i}
                points={polygon.map((p) => `${p[0] ?? 0},${-(p[1] ?? 0)}`).join(' ')}
              />
            ))}
          </g>
        )}

        <ClusterLayer
          clusters={clusters}
          selectedPlantingId={selectedPlantingId}
          freshPlantingId={freshPlantingId}
          onSelectCluster={onSelectCluster}
          onGrabCluster={onGrabCluster}
          spacing={spacing}
          onShowInfo={onShowClusterInfo}
        />

        {viewpoint !== null && (
        <g className="viewpoint" data-testid="viewpoint">
          <circle cx={viewpoint.x} cy={-viewpoint.y} r={0.35} />
          <title>Standpunkt</title>
        </g>
      )}

      {draft.length > 0 && (
          <g data-testid="draft" className="draft">
            <polyline points={svgPoints(draft)} className="draft__line" />
            {draft.map((p) => (
              <circle key={`${p.x},${p.y}`} cx={p.x} cy={-p.y} r={spacing * 0.12} />
            ))}
          </g>
        )}
    </g>
  );
}
