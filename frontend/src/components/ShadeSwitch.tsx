import type { LightMap } from '../api/client';
import { BANDS, type MapMode, bandFor } from './SunMap';

interface Props {
  map: LightMap | null;
  on: boolean;
  mode: MapMode;
  onToggle: (on: boolean) => void;
  onMode: (mode: MapMode) => void;
  onRebuild: () => void;
  busy: boolean;
}

/** What share of the garden's sun falls before the sun crosses due south. */
function morningShare(map: LightMap): number {
  const total = map.hours.reduce((sum, h) => sum + h, 0);
  if (total <= 0) return 0;
  const morning = map.morning.reduce((sum, h) => sum + h, 0);
  return Math.round((morning / total) * 100);
}

/** German short date from an ISO timestamp, or the raw string if it is not one. */
function whenText(iso: string): string {
  const at = new Date(iso);
  if (Number.isNaN(at.getTime())) return iso;
  return at.toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
  });
}

/**
 * The switch that puts the sun map over the plan, and what it means.
 *
 * The legend carries the **numbers**. "Darker means less sun" is not a reading;
 * "3 Stunden" is, and a gardener buying a plant labelled *Halbschatten* needs
 * the one they can compare against the label.
 *
 * It also says when the map was computed, and offers to rebuild it. That is not
 * decoration: the map is stored because it costs half a second to make, so it
 * can be out of date — and a map that is quietly out of date is worse than one
 * that admits it.
 */
export function ShadeSwitch({
  map, on, mode, onToggle, onMode, onRebuild, busy,
}: Props) {
  return (
    <section className="panel shade-switch" aria-labelledby="shade-heading">
      <h2 id="shade-heading">Sonne und Schatten</h2>

      <label className="shade-switch__toggle">
        <input
          type="checkbox"
          checked={on}
          disabled={map === null}
          onChange={(e) => onToggle(e.target.checked)}
        />
        Über dem Plan anzeigen
      </label>

      {map === null ? (
        <p className="hint">
          Noch nichts gezeichnet. Sobald der Garten steht, rechnen wir aus, wie
          viel Sonne wo ankommt.
        </p>
      ) : (
        <>
          <div className="shade-switch__modes" role="group" aria-label="Was gezeigt wird">
            {(
              [
                ['sun', 'Sonnenstunden'],
                ['shade', 'Schattenstunden'],
              ] as Array<[MapMode, string]>
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={value === mode ? 'chip chip--on' : 'chip'}
                aria-pressed={value === mode}
                disabled={!on}
                onClick={() => onMode(value)}
              >
                {label}
              </button>
            ))}
          </div>

          <ul className="shade-switch__legend">
            {BANDS.map(([lower, label], index) => {
              const upper = index === 0 ? null : BANDS[index - 1]![0];
              return (
                <li key={label}>
                  <span className="shade-switch__swatch" data-band={index} />
                  <span>
                    {upper === null
                      ? `ab ${lower} h`
                      : `${lower}–${upper} h`}{' '}
                    — {label}
                  </span>
                </li>
              );
            })}
          </ul>

          <p className="hint">
            Hellster Punkt im Garten: {map.max_hours.toFixed(1)} h am Tag —{' '}
            {bandFor(map.max_hours)}. Gemittelt über März bis Oktober.
          </p>

          {/* Not a footnote. Afternoon sun is hotter and harsher, and a great
              many species sold as Halbschatten want the morning specifically —
              a total cannot say which four hours a spot gets. */}
          {map.morning.length > 0 && (
            <p className="hint">
              Davon vormittags: {morningShare(map)} %. Vormittagssonne ist
              milder — viele Halbschatten-Arten meinen genau die.
            </p>
          )}

          {map.misplaced.length > 0 && (
            <div className="shade-switch__warnings">
              <h3>Steht im falschen Licht</h3>
              <ul>
                {map.misplaced.map((m) => (
                  <li key={m.planting_id}>
                    <strong>{m.name}</strong>{' '}
                    {m.problem === 'too_dark'
                      ? `steht zu dunkel: ${m.sun_hours} h dort, die Art will mehr.`
                      : `steht zu hell: ${m.sun_hours} h dort, die Art will weniger.`}
                  </li>
                ))}
              </ul>
              {/* A warning, never a refusal. The gardener may know something
                  the model does not — a cultivar bred for shade, a wall that
                  throws light back, or simply that they want it there. */}
              <p className="hint">
                Ein Hinweis, kein Einwand. Wenn du es besser weißt, lass es
                stehen.
              </p>
            </div>
          )}

          <div className="shade-switch__actions">
            <span className="hint">
              {map.stale
                ? 'Seit der letzten Änderung nicht neu gerechnet.'
                : `Berechnet am ${whenText(map.computed_at)}.`}
            </span>
            <button type="button" disabled={busy} onClick={onRebuild}>
              Schatten neu berechnen
            </button>
          </div>
        </>
      )}
    </section>
  );
}
