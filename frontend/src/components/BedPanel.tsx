import { useState } from 'react';

import type { GardenOut } from '../api/client';
import { KINDS } from '../kinds';
import { bedName, beds as bedCount, obstacles as obstacleCount, species } from '../plural';

interface Props {
  garden: GardenOut;
  selectedBedId: number | null;
  onSelectBed: (bedId: number) => void;
  onAddBed: (bed: {
    name: string;
    polygon: number[][];
    soil_type: string;
    moisture: string;
  }) => Promise<void>;
  onAddObstacle: (obstacle: {
    kind: string;
    x: number;
    y: number;
    width: number;
    depth: number;
    /** Absent for surfaces, which have none. */
    height?: number;
  }) => Promise<void>;
  busy: boolean;
}

const SOILS = ['sand', 'loam', 'clay', 'humus'] as const;
const MOISTURES = ['dry', 'fresh', 'moist', 'wet'] as const;

/** A rectangle is enough to place a bed by keyboard; the canvas is the faster path. */
function rectangle(x: number, y: number, w: number, h: number): number[][] {
  return [
    [x, y],
    [x + w, y],
    [x + w, y + h],
    [x, y + h],
  ];
}

function lightText(bed: GardenOut['beds'][number]): string {
  // Unknown renders as unknown — never as 0 h, at any layer.
  if (bed.sun_hours === null || bed.ellenberg_l === null) {
    return 'noch nicht berechnet';
  }
  return `${bed.sun_hours.toFixed(1)} h/Tag · L ${bed.ellenberg_l}`;
}

/**
 * The button's accessible name is computed from its children, and adjacent spans
 * concatenate without a space — a screen reader would say "Neues Beetnoch nicht
 * berechnet". Spelling the name out avoids relying on that.
 */
function bedButtonLabel(bed: GardenOut['beds'][number]): string {
  const planted =
    bed.plantings.length === 0
      ? 'nichts gepflanzt'
      : `${species(bed.plantings.length)} gepflanzt`;
  return `${bedName(bed.name)}, ${lightText(bed)}, ${planted}`;
}

export function BedPanel({
  garden,
  selectedBedId,
  onSelectBed,
  onAddBed,
  onAddObstacle,
  busy,
}: Props) {
  const [bedName, setBedName] = useState('Neues Beet');
  const [bedX, setBedX] = useState('0');
  const [bedY, setBedY] = useState('0');
  const [bedW, setBedW] = useState('3');
  const [bedH, setBedH] = useState('2');
  const [soil, setSoil] = useState<string>('loam');
  const [moisture, setMoisture] = useState<string>('fresh');

  const [obstacleKind, setObstacleKind] = useState('wall');
  const [obstacleX, setObstacleX] = useState('0');
  const [obstacleY, setObstacleY] = useState('-4');
  const [obstacleWidth, setObstacleWidth] = useState('6');
  const [obstacleDepth, setObstacleDepth] = useState('0.3');
  const [obstacleHeight, setObstacleHeight] = useState('2');

  /**
   * Choosing a kind fills in what that kind usually is.
   *
   * The same rule as the object editor: picking "Hecke" should answer
   * questions, not ask three more.
   */
  const chooseKind = (kind: string) => {
    setObstacleKind(kind);
    const chosen = KINDS.find((k) => k.kind === kind);
    if (chosen === undefined) return;
    const [width, depth] = chosen.size
      .replace(/ m.*$/, '')
      .split(' × ')
      .map((part) => part.replace(',', '.'));
    if (width !== undefined) setObstacleWidth(width);
    setObstacleDepth(depth ?? width ?? '');
    setObstacleHeight(chosen.height === null ? '' : String(chosen.height));
  };

  return (
    <div className="panel">
      <h2>{garden.name}</h2>
      <p className="hint">
        Standort {garden.latitude}°, {garden.longitude}° · {bedCount(garden.beds.length)} ·{' '}
        {obstacleCount(garden.obstacles.length)}
      </p>

      <h3>Beete</h3>
      {garden.beds.length === 0 ? (
        <p className="hint">Noch keine Beete angelegt.</p>
      ) : (
        <ul className="bed-list">
          {garden.beds.map((bed) => (
            <li key={bed.bed_id}>
              <button
                type="button"
                className={bed.bed_id === selectedBedId ? 'bed-button is-selected' : 'bed-button'}
                aria-pressed={bed.bed_id === selectedBedId}
                aria-label={bedButtonLabel(bed)}
                onClick={() => onSelectBed(bed.bed_id)}
              >
                <span className="bed-button__name">{bed.name}</span>
                <span className="bed-button__light">{lightText(bed)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void onAddBed({
            name: bedName,
            polygon: rectangle(
              Number.parseFloat(bedX),
              Number.parseFloat(bedY),
              Number.parseFloat(bedW),
              Number.parseFloat(bedH),
            ),
            soil_type: soil,
            moisture,
          });
        }}
      >
        <h3>Beet hinzufügen</h3>
        <label htmlFor="bed-name">Name</label>
        <input id="bed-name" value={bedName} onChange={(e) => setBedName(e.target.value)} required />

        <div className="row">
          <div>
            <label htmlFor="bed-x">x (m, Ost)</label>
            <input id="bed-x" type="number" step="any" value={bedX}
                   onChange={(e) => setBedX(e.target.value)} />
          </div>
          <div>
            <label htmlFor="bed-y">y (m, Nord)</label>
            <input id="bed-y" type="number" step="any" value={bedY}
                   onChange={(e) => setBedY(e.target.value)} />
          </div>
          <div>
            <label htmlFor="bed-w">Breite</label>
            <input id="bed-w" type="number" step="any" min="0.5" value={bedW}
                   onChange={(e) => setBedW(e.target.value)} />
          </div>
          <div>
            <label htmlFor="bed-h">Tiefe</label>
            <input id="bed-h" type="number" step="any" min="0.5" value={bedH}
                   onChange={(e) => setBedH(e.target.value)} />
          </div>
        </div>

        <div className="row">
          <div>
            <label htmlFor="bed-soil">Boden</label>
            <select id="bed-soil" value={soil} onChange={(e) => setSoil(e.target.value)}>
              {SOILS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="bed-moisture">Feuchte</label>
            <select id="bed-moisture" value={moisture}
                    onChange={(e) => setMoisture(e.target.value)}>
              {MOISTURES.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>
        <button type="submit" disabled={busy}>Beet hinzufügen</button>
      </form>

      <form
        aria-label="Hindernis hinzufügen"
        onSubmit={(event) => {
          event.preventDefault();
          void onAddObstacle({
            kind: obstacleKind,
            x: Number.parseFloat(obstacleX),
            y: Number.parseFloat(obstacleY),
            width: Number.parseFloat(obstacleWidth),
            depth: Number.parseFloat(obstacleDepth),
            // A surface has no height, and inventing one would have paving
            // cast a shadow.
            ...(obstacleHeight === ''
              ? {}
              : { height: Number.parseFloat(obstacleHeight) }),
          });
        }}
      >
        <h3>Hindernis hinzufügen</h3>
        {/* step="any" throughout: the fields once carried step="0.5" over a
            min of 0.2, which makes 6 m an invalid value. An invalid number
            input blocks submission silently — the button simply did nothing. */}
        <p className="hint">
          Nach dem Hinzufügen berechnet der Server das Licht aller Beete neu.
        </p>
        <div className="row">
          <div>
            <label htmlFor="obs-kind">Art</label>
            {/* A select, not a free text field: the server takes a closed set,
                so anything typed here that is not in it is a 422 the user has
                no way to predict. */}
            <select id="obs-kind" value={obstacleKind}
                    onChange={(e) => chooseKind(e.target.value)}>
              {KINDS.map((k) => (
                <option key={k.kind} value={k.kind}>{k.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="obs-x">x (m)</label>
            <input id="obs-x" type="number" step="any" value={obstacleX}
                   onChange={(e) => setObstacleX(e.target.value)} />
          </div>
          <div>
            <label htmlFor="obs-y">y (m)</label>
            <input id="obs-y" type="number" step="any" value={obstacleY}
                   onChange={(e) => setObstacleY(e.target.value)} />
          </div>
          <div>
            <label htmlFor="obs-w">Breite</label>
            <input id="obs-w" type="number" step="any" min="0.2" value={obstacleWidth}
                   onChange={(e) => setObstacleWidth(e.target.value)} />
          </div>
          <div>
            <label htmlFor="obs-d">Tiefe</label>
            <input id="obs-d" type="number" step="any" min="0.2" value={obstacleDepth}
                   onChange={(e) => setObstacleDepth(e.target.value)} />
          </div>
          <div>
            <label htmlFor="obs-h">Höhe</label>
            <input id="obs-h" type="number" step="any" min="0.5" value={obstacleHeight}
                   onChange={(e) => setObstacleHeight(e.target.value)} />
          </div>
        </div>
        <button type="submit" disabled={busy}>Hindernis hinzufügen</button>
      </form>
    </div>
  );
}
