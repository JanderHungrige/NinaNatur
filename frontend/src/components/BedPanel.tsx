import type { GardenOut } from '../api/client';
import { bedName, beds as bedCount, obstacles as obstacleCount, species } from '../plural';
import { slopeSentence } from '../slopes';

interface Props {
  garden: GardenOut;
  selectedBedId: number | null;
  onSelectBed: (bedId: number) => void;
}


/** A rectangle is enough to place a bed by keyboard; the canvas is the faster path. */
export function lightText(bed: GardenOut['beds'][number]): string {
  // Unknown renders as unknown — never as 0 h, at any layer.
  if (bed.sun_hours === null || bed.ellenberg_l === null) {
    return 'noch nicht berechnet';
  }
  // L on EIVE's 0–10 scale since 2026-09-21, and continuous: one decimal is
  // already finer than the model knows, and "L 7.8125" claimed more.
  const light = [
    `${bed.sun_hours.toFixed(1)} h/Tag`,
    ...skyTexts(bed),
    `L ${bed.ellenberg_l.toFixed(1)}`,
  ].join(' · ');
  // The slope is said, never scored. At this latitude it barely moves the
  // hours; what it moves is the energy per square metre, which this model does
  // not compute — so it belongs beside the figure rather than inside it.
  const fall = slopeSentence(bed.slope_deg, bed.aspect_deg);
  return fall === null || fall === 'eben' ? light : `${light} · ${fall}`;
}

/**
 * What the sky adds to a bed (doc 118): the sunshine to expect with the
 * climate's cloud, the share of the sky it sees, and its light as a share of
 * open ground's. Left out on a bed whose light was computed before them.
 */
function skyTexts(bed: GardenOut['beds'][number]): string[] {
  return [
    bed.expected_sun_h === null ? null : `erwartbar ${bed.expected_sun_h.toFixed(1)} h`,
    bed.sky_view === null ? null : `sieht ${Math.round(bed.sky_view * 100)} % des Himmels`,
    bed.relative_light === null
      ? null : `${Math.round(bed.relative_light * 100)} % des Freilandlichts`,
  ].filter((text): text is string => text !== null);
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
      {/* The garden view's heading, focused when the details change view (doc 88). */}
      <h2 tabIndex={-1} data-view-heading>
        {garden.name}
      </h2>
      <p className="hint">
        Standort {garden.latitude}°, {garden.longitude}° · {bedCount(garden.beds.length)} ·{' '}
        {obstacleCount(garden.obstacles.length)}
      </p>

      <h3>Beete</h3>
      {garden.beds.length === 0 ? (
        // An empty panel names its next step (doc 92).
        <p className="next-step">
          Noch keine Beete. <span aria-hidden="true">→</span> Wähle eine Form aus den Werkzeugen und
          zeichne das erste Beet in den Plan.
        </p>
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
