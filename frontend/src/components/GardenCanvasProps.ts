import type { CanopySuggestion, GardenOut, Landcover, LightMap, Terrain } from '../api/client';
import type { Cluster } from '../canvas/clusters';
import type { Box } from '../canvas/handles';
import type { DrawnShape, Tool } from '../canvas/shapes';
import type { MapMode } from './SunMap';

/** What the garden plan is given. Its own file since doc 87, B1, which kept
 *  GardenCanvas.tsx under the 300-line rule. */
export interface GardenCanvasProps {
  garden: GardenOut;
  selectedBedId: number | null;
  onSelectBed: (bedId: number) => void;
  /**
   * Overrides the measured size. Tests pass it because jsdom lays nothing out;
   * in the browser the element measures itself, since assuming 800×600 for a
   * surface that is actually 633×292 converts every click to the wrong metre.
   */
  size?: { widthPx: number; heightPx: number } | undefined;
  onDrawBed?: ((polygon: number[][]) => void) | undefined;
  onSelectObstacle?: ((obstacleId: number) => void) | undefined;
  /** Every planting as a patch, ready to draw. */
  clusters?: Cluster[] | undefined;
  selectedPlantingId?: number | null;
  /** A patch that was just planted, marked for a moment (doc 88). */
  freshPlantingId?: number | null;
  onSelectCluster?: ((plantingId: number) => void) | undefined;
  /** Dragging a patch to another spot in its bed. */
  onMoveCluster?: ((plantingId: number, to: { x: number; y: number }) => void) | undefined;
  /** The same panel the suggestion list opens. */
  onShowClusterInfo?: ((taxonId: number, name: string) => void) | undefined;
  sunMap?: { map: LightMap; mode: MapMode } | undefined;
  /** The ground the garden stands on, drawn beneath the plan. */
  terrain?: Terrain | null | undefined;
  /** The land around the garden, from OpenStreetMap (doc 114): decoration,
   *  drawn whether the shade is on or not, and credited under the plan. */
  landcover?: Landcover | null | undefined;
  shadows?: number[][][] | undefined;
  /** Where the user is standing, if anywhere. */
  viewpoint?: { x: number; y: number } | null;
  /** Placing one, while the rail's Standpunkt is armed (doc 89). */
  onPlaceViewpoint?: ((x: number, y: number) => void) | undefined;
  /** Trees the surface model found, marked where they stand (doc 89). */
  canopies?: CanopySuggestion[] | undefined;
  /** The plan's "N gefundene Bäume": show their card. */
  onShowFoundTrees?: (() => void) | undefined;
  /** The shape tool that is armed, if any. A drag then draws instead of panning. */
  tool?: Tool | null;
  /** What the armed tool expects, floated in the drawing's own corner. It hangs
   *  inside the stage, not under it, so a caption beneath the drawing — whose
   *  hand it is in (doc 98) — has a line of its own. Seven seconds each
   *  (`PlanHint`). */
  hint?: string;
  onDrawShape?: ((shape: DrawnShape) => void) | undefined;
  /** A freehand stroke: an outline the hand closed, or a path. */
  onDrawTrace?:
    | ((trace: { kind: 'area' | 'path'; points: number[][] }) => void)
    | undefined;
  /** Escape and "Abbrechen" put the tool down; the parent owns which one it is. */
  onCancelTool?: (() => void) | undefined;
  /** Escape also drops whatever is selected — one key out of everything. */
  onClearSelection?: (() => void) | undefined;
  /** Right-click on an element: the short way to say what it is. */
  onAskWhatItIs?:
    | ((id: number, at: { x: number; y: number }) => void)
    | undefined;
  /** Dragging a shape's body moves it, by how far in metres. Not the ground, a
   *  house or a street (doc 87, B1). */
  onMoveObstacle?: ((id: number, by: { x: number; y: number }) => void) | undefined;
  /** The object wearing handles. Selection is the parent's, because the panel
   *  and the plan must agree on what is being edited. */
  selectedObstacleId?: number | null;
  onResizeObstacle?: ((obstacleId: number, box: Box) => void) | undefined;
  /** Editing the outline itself, corner by corner. */
  onReshapeObstacle?: ((obstacleId: number, points: number[][]) => void) | undefined;
}
