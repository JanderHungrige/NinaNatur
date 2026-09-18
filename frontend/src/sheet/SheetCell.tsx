import { useMemo } from 'react';

import { clustersFor } from '../canvas/clusters';
import { type Viewport, gridSpacing, viewBox } from '../canvas/viewport';
import { CanvasScene } from '../components/CanvasScene';
import { PlanFurniture } from '../components/PlanFurniture';
import { SHEET_MONTH, type SheetGarden, coloursFor } from './gardens';
import { sunMapFor } from './light';

/** Where a cell looks: the garden's centre, `spanM` across, in a cell of this size. */
export function cellView(entry: SheetGarden, spanM: number, width: number, height: number): Viewport {
  return { centreX: entry.centre.x, centreY: entry.centre.y, spanM, widthPx: width, heightPx: height };
}

interface Props {
  entry: SheetGarden;
  spanM: number;
  /** The sun map laid over the ground, as the shade switch lays it. */
  sun: boolean;
  width: number;
  height: number;
}

const nothing = (): void => undefined;

/**
 * One cell of the contact sheet (doc 95): the app's own scene, at one zoom, in
 * the paper the app draws it on. Nothing in here draws — the sheet is a way of
 * looking at the plan, and the moment it drew anything of its own it would be
 * looking at itself.
 */
export function SheetCell({ entry, spanM, sun, width, height }: Props) {
  const view = cellView(entry, spanM, width, height);
  const clusters = useMemo(() => {
    const colours = coloursFor(entry.garden);
    return entry.garden.beds.flatMap((b) => clustersFor(b.polygon, b.plantings, colours, SHEET_MONTH));
  }, [entry]);
  const sunMap = useMemo(
    () => (sun ? { map: sunMapFor(entry.garden), mode: 'hours' as const } : undefined),
    [entry, sun],
  );
  return (
    <div className="sheet-cell" style={{ position: 'relative', width, height }}>
      <svg className="canvas" data-testid="canvas-surface" viewBox={viewBox(view)} role="img"
           aria-label={`${entry.title}, ${spanM} m`}>
        <CanvasScene garden={entry.garden} view={view} spacing={gridSpacing(view)}
                     selectedBedId={null} draft={[]} onSelectBed={nothing}
                     clusters={clusters} sunMap={sunMap} />
      </svg>
      {/* The plan's corner, as GardenCanvas puts it there: nothing for Technisch. */}
      <PlanFurniture metresPerPixel={spanM / width} title={entry.title}
                     updatedAt={entry.garden.updated_at} />
    </div>
  );
}
