interface Props {
  gridSpacingM: number;
  drawing: boolean;
  draftPoints: number;
  canUndo: boolean;
  canRedo: boolean;
  problem: string | null;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onStartDrawing: () => void;
  onFinish: () => void;
  onCancel: () => void;
  onUndo: () => void;
  onRedo: () => void;
  placing?: boolean | undefined;
  onPlaceViewpoint?: (() => void) | undefined;
}

function points(n: number): string {
  return `${n} ${n === 1 ? 'Punkt' : 'Punkte'}`;
}

/**
 * The controls above the plan.
 *
 * Zoom is here as buttons and not only as a wheel gesture: a wheel-only zoom
 * locks out anyone without a wheel or trackpad, and anyone whose hands do not
 * do precise scrolls. The wheel is the shortcut; these are the control.
 */
export function CanvasControls({
  gridSpacingM,
  drawing,
  draftPoints,
  canUndo,
  canRedo,
  problem,
  onZoomIn,
  onZoomOut,
  onStartDrawing,
  onFinish,
  onCancel,
  onUndo,
  onRedo,
  placing,
  onPlaceViewpoint,
}: Props) {
  return (
    <div className="canvas-controls">
      <div className="canvas-controls__row">
        <button type="button" onClick={onZoomIn} aria-label="Hineinzoomen">
          +
        </button>
        <button type="button" onClick={onZoomOut} aria-label="Herauszoomen">
          −
        </button>
        {/* The spacing in words, because a grid that silently stops being one
            metre still looks like a measurement. */}
        <span className="canvas-controls__scale" aria-live="polite">
          Raster {gridSpacingM} m
        </span>

        {drawing ? (
          <>
            <span className="canvas-controls__draft">{points(draftPoints)}</span>
            <button type="button" onClick={onFinish}>
              Fertig
            </button>
            <button type="button" className="link-button" onClick={onCancel}>
              Abbrechen
            </button>
          </>
        ) : (
          <button type="button" onClick={onStartDrawing}>
            Beet zeichnen
          </button>
        )}

        {onPlaceViewpoint !== undefined && (
          <button
            type="button"
            aria-pressed={placing === true}
            onClick={onPlaceViewpoint}
          >
            {placing === true ? 'Standpunkt: klicke in den Plan' : 'Standpunkt setzen'}
          </button>
        )}

        <button type="button" onClick={onUndo} disabled={!canUndo} aria-label="Rückgängig">
          ↶
        </button>
        <button
          type="button"
          onClick={onRedo}
          disabled={!canRedo}
          aria-label="Wiederherstellen"
        >
          ↷
        </button>
      </div>

      {drawing && (
        <p className="hint">
          Klicke die Ecken des Beetes. Punkte rasten auf dem Raster ein — halte
          Alt gedrückt, um frei zu setzen. Escape bricht ab. Zoomen: Knöpfe oben
          oder Strg/Cmd + Mausrad.
        </p>
      )}
      {problem !== null && (
        <p className="hint canvas-controls__problem" role="alert">
          {problem}
        </p>
      )}
    </div>
  );
}
