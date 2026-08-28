import { useState } from 'react';

import type { GardenOut } from '../api/client';
import { beds as bedCount, obstacles as obstacleCount } from '../plural';

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
    radius: number;
    height: number;
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
      : `${bed.plantings.length} Art(en) gepflanzt`;
  return `Beet ${bed.name}, ${lightText(bed)}, ${planted}`;
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
  const [obstacleRadius, setObstacleRadius] = useState('5');
  const [obstacleHeight, setObstacleHeight] = useState('6');

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
            <input id="bed-x" type="number" step="0.5" value={bedX}
                   onChange={(e) => setBedX(e.target.value)} />
          </div>
          <div>
            <label htmlFor="bed-y">y (m, Nord)</label>
            <input id="bed-y" type="number" step="0.5" value={bedY}
                   onChange={(e) => setBedY(e.target.value)} />
          </div>
          <div>
            <label htmlFor="bed-w">Breite</label>
            <input id="bed-w" type="number" step="0.5" min="0.5" value={bedW}
                   onChange={(e) => setBedW(e.target.value)} />
          </div>
          <div>
            <label htmlFor="bed-h">Tiefe</label>
            <input id="bed-h" type="number" step="0.5" min="0.5" value={bedH}
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
        onSubmit={(event) => {
          event.preventDefault();
          void onAddObstacle({
            kind: obstacleKind,
            x: Number.parseFloat(obstacleX),
            y: Number.parseFloat(obstacleY),
            radius: Number.parseFloat(obstacleRadius),
            height: Number.parseFloat(obstacleHeight),
          });
        }}
      >
        <h3>Hindernis hinzufügen</h3>
        <p className="hint">
          Nach dem Hinzufügen berechnet der Server das Licht aller Beete neu.
        </p>
        <div className="row">
          <div>
            <label htmlFor="obs-kind">Art</label>
            <input id="obs-kind" value={obstacleKind}
                   onChange={(e) => setObstacleKind(e.target.value)} required />
          </div>
          <div>
            <label htmlFor="obs-x">x (m)</label>
            <input id="obs-x" type="number" step="0.5" value={obstacleX}
                   onChange={(e) => setObstacleX(e.target.value)} />
          </div>
          <div>
            <label htmlFor="obs-y">y (m)</label>
            <input id="obs-y" type="number" step="0.5" value={obstacleY}
                   onChange={(e) => setObstacleY(e.target.value)} />
          </div>
          <div>
            <label htmlFor="obs-r">Radius</label>
            <input id="obs-r" type="number" step="0.5" min="0.5" value={obstacleRadius}
                   onChange={(e) => setObstacleRadius(e.target.value)} />
          </div>
          <div>
            <label htmlFor="obs-h">Höhe</label>
            <input id="obs-h" type="number" step="0.5" min="0.5" value={obstacleHeight}
                   onChange={(e) => setObstacleHeight(e.target.value)} />
          </div>
        </div>
        <button type="submit" disabled={busy}>Hindernis hinzufügen</button>
      </form>
    </div>
  );
}
