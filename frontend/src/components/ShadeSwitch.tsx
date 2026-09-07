import type { LightMap, Terrain } from '../api/client';
import { LEVELS, type MapMode, bandFor } from './SunMap';

interface Props {
  /** The ground under the garden, or null where nobody publishes it. */
  terrain?: Terrain | null | undefined;
  map: LightMap | null;
  on: boolean;
  mode: MapMode;
  /** Null for the whole season. 3–10 for one month of it. */
  month: number | null;
  onToggle: (on: boolean) => void;
  onMode: (mode: MapMode) => void;
  onMonth: (month: number | null) => void;
  onRebuild: () => void;
  busy: boolean;
}

/** March to October, the window the whole light model works in. */
const MONTHS: ReadonlyArray<readonly [number, string]> = [
  [3, 'März'], [4, 'April'], [5, 'Mai'], [6, 'Juni'], [7, 'Juli'],
  [8, 'August'], [9, 'September'], [10, 'Oktober'],
];

/** What share of the garden's sun falls before the sun crosses due south. */
function morningShare(map: LightMap): number {
  // Ground only. A roof's hours are a real answer to a different question, and
  // nothing is planted on one — so they belong in neither half of this.
  const ground = (values: (number | null)[]) =>
    values.reduce(
      (sum: number, value, index) =>
        sum + (map.roof[index] === true ? 0 : (value ?? 0)),
      0,
    );
  const total = ground(map.hours);
  if (total <= 0) return 0;
  const morning = ground(map.morning);
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
 * the one they can compare against the label. It is also the only thing that
 * says what the two inks mean, so it is painted by the map's own `washFor`
 * rather than by a parallel set of colours that could drift from it.
 *
 * The rebuild button is the **first** thing in the panel, not a footnote under
 * the legend. Nothing recomputes the light on a write any more — a garden of
 * forty obstacles cost 3.3 s per bed, which turned drawing a bed into a wait —
 * so the button is the only thing that makes a map at all. A control that is
 * the sole way to get the feature cannot sit below five paragraphs, and it has
 * to be there before the first map exists.
 */
export function ShadeSwitch({
  map, terrain, on, mode, month, onToggle, onMode, onMonth, onRebuild, busy,
}: Props) {
  return (
    <section className="panel shade-switch" aria-labelledby="shade-heading">
      <h2 id="shade-heading">Sonne und Schatten</h2>

      {/* Outside the `map === null` branch on purpose: a garden that has never
          been computed is exactly the garden that needs this button, and the
          old panel hid it behind "nothing drawn yet". */}
      <div className="shade-switch__rebuild">
        <button type="button" disabled={busy} onClick={onRebuild}>
          Schatten neu berechnen
        </button>
        <p className="hint">
          Nach dem Anlegen neuer Objekte den Schatten einmal neu berechnen — das
          passiert nicht mehr von selbst.
        </p>
        {map !== null && (
          <span className="hint">
            {map.stale
              ? 'Seit der letzten Änderung nicht neu gerechnet.'
              : `Berechnet am ${whenText(map.computed_at)}.`}
          </span>
        )}
      </div>

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
          Noch nichts gezeichnet. Sobald Beete oder Objekte stehen, sagt ein
          Klick auf den Knopf oben, wie viel Sonne wo ankommt.
        </p>
      ) : (
        <>
          <div className="shade-switch__modes" role="group" aria-label="Was gezeigt wird">
            {(
              [
                ['hours', 'Sonnenstunden'],
                ['day', 'Tagesverlauf'],
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

          {/* Two choices, not three drawn at once. The heat map answers "how
              much sun does this corner get all summer"; the moving shadows
              answer "where is the shade at four o'clock". Painting both
              together made each harder to read than either alone. */}
          {mode === 'day' && (
            <p className="hint">
              Zeigt die wandernden Objektschatten über der Sonnenkarte — gelb
              ist viel Sonne. Abspielen unten beim Zeitstrahl.
            </p>
          )}

          {/* A garden with a house to its south is a different garden in April
              and in July, and the season average describes neither. Computed
              on the spot rather than stored: it is a question somebody asks
              while looking, not the number a plant is placed by. */}
          <label className="shade-switch__month">
            Zeitraum
            <select
              value={month ?? 'season'}
              disabled={!on}
              onChange={(e) =>
                onMonth(e.target.value === 'season' ? null : Number(e.target.value))
              }
            >
              <option value="season">Ganze Saison (März–Oktober)</option>
              {MONTHS.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>

          {/* One row per step the map actually draws, so "more yellow" has
              somewhere to be read off. The gardening names sit on the step
              where each band begins; the steps between are increments of the
              same wash, not new names. */}
          <ul className="shade-switch__legend">
            {LEVELS.map((level, index) => {
              const upper = index === 0 ? null : LEVELS[index - 1]!.from;
              return (
                <li key={level.from}>
                  <span
                    className="shade-switch__swatch"
                    data-ink={level.ink ?? 'none'}
                    style={level.ink === null ? undefined : { opacity: level.strength * 0.8 }}
                  />
                  <span>
                    {upper === null ? `ab ${level.from} h` : `${level.from}–${upper} h`}
                    {level.name !== undefined && ` — ${level.name}`}
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

          <TerrainNote terrain={terrain} />

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
        </>
      )}
    </section>
  );
}


/**
 * Where the ground came from, and how far to trust it.
 *
 * Not a footnote. Every height in this model is somebody else's measurement
 * under somebody else's licence, and a number shown without either invites more
 * confidence than it has earned — as well as being, for dl-de/by-2-0 and
 * CC-BY-4.0, a use outside the licence.
 *
 * The silent case is the one worth having: a garden in a Bundesland with no
 * open service is computed on flat ground, exactly as every garden was before
 * Wave 17, and the page says so rather than letting the reader assume the
 * hillside was taken into account.
 */
function TerrainNote({ terrain }: { terrain?: Terrain | null | undefined }) {
  if (terrain === undefined) return null;
  if (terrain === null) {
    return (
      <p className="hint">
        Für diese Adresse liegen keine Höhendaten vor — der Plan rechnet mit
        ebenem Gelände.
      </p>
    );
  }
  const fall = Math.round((terrain.highest - terrain.lowest) * 10) / 10;
  const coarse = terrain.vertical_step_m >= 1;
  return (
    <p className="hint">
      Gelände {terrain.lowest.toFixed(0)}–{terrain.highest.toFixed(0)} m ü. NHN,{' '}
      {fall} m Unterschied · {terrain.attribution}
      {coarse
        ? ' · Höhen nur in ganzen Metern — feinere Neigungen sieht dieser Dienst nicht.'
        : ' · Gitterweite 1 m, Höhengenauigkeit etwa ± 0,3 m.'}
    </p>
  );
}
