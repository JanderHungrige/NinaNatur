import { useState } from 'react';

interface Props {
  soilType: string | null;
  moisture: string | null;
  onSave: (soilType: string, moisture: string) => void;
  busy: boolean;
}

const SOILS: Array<[string, string]> = [
  ['sand', 'Sandig — rieselt, trocknet schnell'],
  ['loam', 'Lehmig — formbar, hält Wasser'],
  ['clay', 'Tonig — schwer, klebt nass'],
  ['humus', 'Humos — dunkel, krümelig'],
];

const MOISTURES: Array<[string, string]> = [
  ['dry', 'Trocken'],
  ['fresh', 'Frisch'],
  ['moist', 'Feucht'],
  ['wet', 'Nass'],
];

/**
 * What the ground is, asked once for the whole garden.
 *
 * One question per garden rather than one per bed — the shape Wave 8 settled on
 * for building heights. Asking it of every bed puts a wall in front of somebody
 * who has just arrived, and the answer is the same for most of a garden anyway.
 *
 * The descriptions are what a hand in the soil tells you, not a classification:
 * "rieselt, trocknet schnell" is answerable in the garden, "podsolierter
 * Braunerde-Gley" is not.
 */
export function GardenSoil({ soilType, moisture, onSave, busy }: Props) {
  const [soil, setSoil] = useState(soilType ?? 'loam');
  const [wet, setWet] = useState(moisture ?? 'fresh');
  const answered = soilType !== null && moisture !== null;

  return (
    <section className="panel garden-soil" aria-labelledby="soil-heading">
      <h2 id="soil-heading">Boden im Garten</h2>
      <p className="hint">
        {answered
          ? 'Gilt als Ausgangswert für neue Beete. Einzelne Beete kannst du davon abweichen lassen — ein Hochbeet mit gekaufter Erde zum Beispiel.'
          : 'Einmal für den ganzen Garten. Jedes Beet, das du danach zeichnest, beginnt damit — und lässt sich einzeln ändern.'}
      </p>

      <label htmlFor="garden-soil">Boden</label>
      <select
        id="garden-soil"
        value={soil}
        disabled={busy}
        onChange={(e) => setSoil(e.target.value)}
      >
        {SOILS.map(([value, label]) => (
          <option key={value} value={value}>{label}</option>
        ))}
      </select>

      <label htmlFor="garden-moisture">Feuchte</label>
      <select
        id="garden-moisture"
        value={wet}
        disabled={busy}
        onChange={(e) => setWet(e.target.value)}
      >
        {MOISTURES.map(([value, label]) => (
          <option key={value} value={value}>{label}</option>
        ))}
      </select>

      <div className="garden-soil__actions">
        <button type="button" disabled={busy} onClick={() => onSave(soil, wet)}>
          {answered ? 'Ändern' : 'Übernehmen'}
        </button>
        {/* Most people do not know their soil type, and guessing it for them
            would put a number into the suggestions that nobody gave. A link is
            what this feature does with an outside source; reading one is
            research for a later wave. */}
        <a
          className="link-button"
          href="https://www.bgr.bund.de/DE/Themen/Boden/Informationsgrundlagen/Bodenkundliche_Karten_Datenbanken/bodenkundliche_karten_datenbanken_node.html"
          target="_blank"
          rel="noreferrer noopener"
        >
          Boden nachschlagen
        </a>
      </div>
      <p className="hint">
        Wenn du unsicher bist: eine Handvoll feuchte Erde drücken. Zerfällt sie,
        ist sie sandig; lässt sie sich zu einer Wurst rollen, ist sie lehmig bis
        tonig.
      </p>
    </section>
  );
}
