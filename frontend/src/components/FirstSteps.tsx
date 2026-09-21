import type { GardenOut, LightMap } from '../api/client';
import { SoilLine } from './SoilLine';
import { Working } from './Working';

interface Props {
  soilType: string | null;
  moisture: string | null;
  onSaveSoil: (soilType: string, moisture: string) => void;
  /** Whether the garden's light has been computed at least once. */
  hasMap: boolean;
  onComputeShade: () => void;
  /** The shade is being computed: the button says so while it waits. */
  computing?: boolean | undefined;
  /** How many beds the garden has. */
  beds: number;
  /** Arms the tool a bed is drawn with. */
  onDrawBed: () => void;
  busy: boolean;
}

export interface Steps {
  soil: boolean;
  shade: boolean;
  bed: boolean;
  all: boolean;
}

/** Which of the three steps a garden has taken — read from the garden, never stored (doc 89). */
export function stepsDone(garden: GardenOut, map: LightMap | null): Steps {
  const soil = garden.soil_type !== null && garden.moisture !== null;
  const shade = map !== null;
  const bed = garden.beds.length > 0;
  return { soil, shade, bed, all: soil && shade && bed };
}

/**
 * The first three steps in a garden, as prompts in the details (doc 89).
 *
 * Soil, shade and a first bed are what a garden needs before a suggestion means
 * anything. The owner chose prompts in the details over an overlay — no modal
 * before the first look — so they stand where the garden's details stand, say in
 * words whether each is done, and are gone once all three are.
 */
export function FirstSteps({
  soilType,
  moisture,
  onSaveSoil,
  hasMap,
  onComputeShade,
  computing = false,
  beds,
  onDrawBed,
  busy,
}: Props) {
  const soil = soilType !== null && moisture !== null;
  /** A press while a request runs does nothing: a disabled button cannot hold
   *  the focus (doc 88, rule 11). */
  const unlessBusy = (action: () => void) => () => {
    if (!busy) action();
  };
  const state = (done: boolean) => <span className="first-steps__state">{done ? 'erledigt' : 'offen'}</span>;
  const stepClass = (done: boolean) => (done ? 'first-steps__step is-done' : 'first-steps__step');

  return (
    <section className="first-steps" aria-labelledby="first-steps-heading">
      <h2 id="first-steps-heading">Drei Schritte zum Anfang</h2>
      <ol className="first-steps__list">
        <li className={stepClass(soil)}>
          <p className="first-steps__label">
            <span className="first-steps__number" aria-hidden="true">1</span>
            Boden {state(soil)}
          </p>
          {/* Doc 48's question, unchanged: once per garden, a link out rather
              than a guess — and once answered, already the line it stays. */}
          <SoilLine soilType={soilType} moisture={moisture} onSave={onSaveSoil} busy={busy} />
        </li>

        <li className={stepClass(hasMap)}>
          <p className="first-steps__label">
            <span className="first-steps__number" aria-hidden="true">2</span>
            Schatten berechnen {state(hasMap)}
          </p>
          {hasMap ? (
            <p className="hint">Berechnet. „Sonne &amp; Schatten“ oben legt die Karte über den Plan.</p>
          ) : (
            <>
              <p className="hint">
                Einmal ausrechnen, wie viel Sonne wo ankommt — die Vorschläge richten
                sich danach. Nach neuen Objekten wieder: das geschieht nicht von selbst.
              </p>
              <button type="button" aria-disabled={busy || undefined} onClick={unlessBusy(onComputeShade)}>
                {computing ? <Working label="Wird berechnet…" /> : 'Schatten berechnen'}
              </button>
            </>
          )}
        </li>

        <li className={stepClass(beds > 0)}>
          <p className="first-steps__label">
            <span className="first-steps__number" aria-hidden="true">3</span>
            Erstes Beet {state(beds > 0)}
          </p>
          {beds > 0 ? (
            <p className="hint">{beds === 1 ? 'Ein Beet' : `${beds} Beete`} gezeichnet.</p>
          ) : (
            <>
              <p className="hint">
                Mit dem Vieleck Ecke für Ecke in den Plan klicken, dann „Fertig“. Danach
                stehen hier die Arten, die hineinpassen.
              </p>
              <button type="button" onClick={onDrawBed}>
                Beet zeichnen
              </button>
            </>
          )}
        </li>
      </ol>
    </section>
  );
}
