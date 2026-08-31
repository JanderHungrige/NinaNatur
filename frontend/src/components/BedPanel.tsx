import type { GardenOut } from '../api/client';
import { bedName, beds as bedCount, obstacles as obstacleCount, species } from '../plural';

interface Props {
  garden: GardenOut;
  selectedBedId: number | null;
  onSelectBed: (bedId: number) => void;
}


/** A rectangle is enough to place a bed by keyboard; the canvas is the faster path. */
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
}: Props) {


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

    </div>
  );
}
