import { memo, useCallback, useMemo } from 'react';

import type { CanopySuggestion, GardenOut, LightMap } from '../api/client';
import type { Cluster } from '../canvas/clusters';
import { usePlanTheme } from '../themes/context';
import { CanopyMarks } from './CanopyMarks';
import { ClusterLayer } from './ClusterLayer';
import { InkLayer, beneathOf, useDecorations } from './PlanDecorations';
import { PlanObjects } from './PlanObjects';
import { type MapMode, SunMap } from './SunMap';

export interface WorldProps {
  garden: GardenOut;
  /** Metres per pixel, in halvings (`planScale`): it changes a few times across
   *  a zoom, never on every frame of one. */
  scale: number;
  spacing: number;
  selectedBedId: number | null;
  selectedObstacleId: number | null;
  viewpoint: { x: number; y: number } | null;
  onSelectBed: (bedId: number) => void;
  onSelectObstacle?: ((obstacleId: number) => void) | undefined;
  armed: boolean;
  onAskWhatItIs?: ((id: number, at: { x: number; y: number }) => void) | undefined;
  onGrabElement?: ((id: number, event: React.PointerEvent) => void) | undefined;
  dragOffset: { id: number; dx: number; dy: number } | null;
  clusters: Cluster[];
  selectedPlantingId: number | null;
  freshPlantingId: number | null;
  onSelectCluster?: ((plantingId: number) => void) | undefined;
  onGrabCluster?: ((plantingId: number, event: React.PointerEvent) => void) | undefined;
  onShowClusterInfo?: ((taxonId: number, name: string) => void) | undefined;
  sunMap?: LightMap | undefined;
  mapMode?: MapMode | undefined;
  shadows?: number[][][] | undefined;
  canopies: CanopySuggestion[];
}

/**
 * Everything on the plan that does not move with the view.
 *
 * Memoised, and given no viewport: a pan or a zoom changes the viewBox and the
 * backdrop, and nothing in here. It used to be rebuilt in full on every pointer
 * move of every pan, every shape and every cell with it (the owner's check,
 * 2026-09-21, #11). What it is given has to stay the same between those frames
 * for that to hold. The canvas passes stable handlers (`useStableHandlers`) and
 * arrays that change only when their contents do.
 */
function World({
  garden, scale, spacing, selectedBedId, selectedObstacleId, viewpoint, onSelectBed,
  onSelectObstacle, armed, onAskWhatItIs, onGrabElement, dragOffset, clusters,
  selectedPlantingId, freshPlantingId, onSelectCluster, onGrabCluster, onShowClusterInfo,
  sunMap, mapMode = 'hours', shadows, canopies,
}: WorldProps) {
  const theme = usePlanTheme();
  // Each shape asks for itself (doc 99), at the scale the decorations use, so
  // a shape's wash and the marks over it are always at the same level.
  const decorations = useDecorations(garden, theme, scale);
  /** Shown where the pointer has it, saved where it is let go. */
  const shift = useCallback((id: number): string =>
    dragOffset !== null && dragOffset.id === id
      ? `translate(${dragOffset.dx} ${-dragOffset.dy})`
      : '', [dragOffset]);
  const beneath = useMemo(() => (decorations === null ? undefined : beneathOf(decorations, shift)),
    [decorations, shift]);

  return (
    <>
      <PlanObjects garden={garden} theme={theme} metresPerPixel={scale} selectedBedId={selectedBedId}
                   selectedObstacleId={selectedObstacleId} armed={armed}
                   onSelectBed={onSelectBed} onSelectObstacle={onSelectObstacle}
                   onAskWhatItIs={onAskWhatItIs} onGrabElement={onGrabElement} shift={shift}
                   beneath={beneath} />
      {decorations !== null
        && <InkLayer drawn={decorations} theme={theme} shift={shift} metresPerPixel={scale}
                     dragOffset={dragOffset} />}

      {sunMap !== undefined && <SunMap map={sunMap} mode={mapMode} />}

      {/* Found trees where they stand (doc 89): a mark over the plan, never a target. */}
      <CanopyMarks trees={canopies} />

      {/* One moment of one day, over everything: while it plays, where the
          shadow is *now* is the only question being asked. Every shadow of the
          moment, as rings — outlines anticlockwise, the holes in them clockwise
          (doc 116) — in one path under the non-zero rule, so a courtyard the
          sun still reaches is drawn open and two that overlap fill once. */}
      {shadows !== undefined && (
        <g className="day-shadows" aria-hidden="true" pointerEvents="none">
          <path
            fillRule="nonzero"
            d={shadows.map((ring) =>
              `M${ring.map((p) => `${p[0] ?? 0},${-(p[1] ?? 0)}`).join('L')}Z`).join('')}
          />
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
    </>
  );
}

export const SceneWorld = memo(World);
