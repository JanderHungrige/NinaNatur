import type { BedSuggestions } from '../api/client';
import { colourLabel } from '../colours';
import { birds, insects } from '../plural';
import { SWATCH } from './ClusterLayer';
import { MonthStrip } from './MonthStrip';

export type Suggestion = BedSuggestions['items'][number];

interface Props {
  item: Suggestion;
  /** Where the row stands in the whole list, counted from nought. */
  index: number;
  /** How long the whole list is. */
  setsize: number;
  /** The row's distance from the top of the list, in pixels. */
  top: number;
  /** Whether this row is the list's one stop in the tab order (doc 90, rule 4). */
  tabbable: boolean;
  /** Whether every row of its window has a third line, so that all keep one height. */
  extraLine: boolean;
  busy: boolean;
  onPlant: (taxonId: number, name: string) => Promise<void>;
  /** The third argument is the catalogue's colour, so the panel can say
   *  whether what it shows came from there or from the gardener. */
  onShowInfo: (taxonId: number, name: string, colour: string | null) => void;
}

const BAND_LABEL: Record<string, string> = {
  optimal: 'optimal',
  suitable: 'passend',
  borderline: 'grenzwertig',
  unsuitable: 'ungeeignet',
};

/** Weakest first: a fit is as good as its worst axis. */
const BANDS = ['unsuitable', 'borderline', 'suitable', 'optimal'];

const AXIS_LABEL: Record<string, string> = {
  ellenberg_l: 'Licht',
  ellenberg_m: 'Feuchte',
  ellenberg_n: 'Nährstoffe',
  ellenberg_r: 'pH',
};

/** The colour, and whose word it is.
 *
 * The gardener's own answer wins over the catalogue's — they looked at the
 * plant — but it says so, because a value the user typed and a value from GIFT
 * are not the same kind of fact and this app cites every number it shows.
 */
function describeColour(item: Suggestion): string {
  if (item.observed_colour != null) return `${colourLabel(item.observed_colour)} (von dir)`;
  if (item.flower_colour === null) return 'Farbe unbekannt';
  return colourLabel(item.flower_colour);
}

/** "braucht ~201 m²" for a plant larger than its bed. Priced, not hidden: a tree
 *  in a small bed is a decision the gardener is entitled to make (doc 25). */
function roomFor(item: Suggestion): string | null {
  return item.fits_bed === false && item.space_m2 !== null
    ? `braucht ~${Math.round(item.space_m2)} m²`
    : null;
}

/** The birds recorded eating it, when there are any. A "0 Vogelarten" on every
 *  herbaceous plant is noise, and on a species GloBI holds no records for at
 *  all it would be a claim the data cannot support. */
function birdsFor(item: Suggestion): string | null {
  return item.bird_partners !== null && item.bird_partners > 0
    ? `${birds(item.bird_partners)} als Nahrung`
    : null;
}

/** "214 Insektenarten": what the list's order weighs beside the growing
 *  conditions, on the row so the order can be argued with. Nothing where GloBI
 *  records none — "0" would claim the data knows there are none. */
function insectsFor(item: Suggestion): string | null {
  const n = item.insect_partners ?? null;
  return n !== null && n > 0 ? insects(n) : null;
}

/** Whether a row has room or birds to show: what a third line is for. */
export function hasExtraLine(item: Suggestion): boolean {
  return roomFor(item) !== null || birdsFor(item) !== null;
}

interface Fit {
  band: string;
  /** What the badge shows: the weakest axis, or "optimal" when none is weaker. */
  short: string;
  /** Every axis, "Licht optimal · Feuchte grenzwertig". */
  full: string;
  /** The same, as a screen reader says it. */
  spoken: string;
}

function readFit(axes: Suggestion['fit']['axes']): Fit | null {
  const readings = Object.entries(axes).map(([axis, fit]) => ({
    band: String(fit.band),
    words: `${AXIS_LABEL[axis] ?? axis} ${BAND_LABEL[fit.band] ?? fit.band}`,
  }));
  let weakest = readings[0];
  for (const reading of readings) {
    if (weakest !== undefined && BANDS.indexOf(reading.band) < BANDS.indexOf(weakest.band)) {
      weakest = reading;
    }
  }
  if (weakest === undefined) return null;
  const words = readings.map((reading) => reading.words);
  return {
    band: weakest.band,
    short: weakest.band === 'optimal' ? 'optimal' : weakest.words,
    full: words.join(' · '),
    spoken: words.join(', '),
  };
}

/** The flower colour as a dot and a word. The word gives way before the fit
 *  badge does; its whole stays in the title. */
function ColourMark({ item }: { item: Suggestion }) {
  const colour = item.observed_colour ?? item.flower_colour;
  const swatch = colour != null ? SWATCH[colour] : undefined;
  const words = describeColour(item);
  return (
    <span className="suggestion-row__colour" title={words}>
      <svg
        className={colour == null ? 'suggestion-row__dot suggestion-row__dot--unknown' : 'suggestion-row__dot'}
        viewBox="0 0 10 10"
        aria-hidden="true"
      >
        <circle cx="5" cy="5" r="4" style={swatch !== undefined ? { fill: swatch } : undefined} />
      </svg>
      <span className="suggestion-row__colour-word">{words}</span>
    </span>
  );
}

/** "214 Insektenarten", or nothing where GloBI records none. */
function InsectCount({ item }: { item: Suggestion }) {
  const visited = insectsFor(item);
  if (visited === null) return null;
  return (
    <span className="suggestion-row__insects" title={`${visited}, in Deutschland als Partner dieser Pflanze erfasst`}>
      {visited}
    </span>
  );
}

/**
 * One suggestion as one compact row (doc 90): its name, which opens what is
 * known about the species; its colour, months, insects and fit on the second
 * line; room and birds on a third when its window has any; and a button to
 * plant it.
 */
export function SuggestionRow(props: Props) {
  const { item, index, setsize, top, tabbable, extraLine, busy, onPlant, onShowInfo } = props;
  const stop = tabbable ? 0 : -1;
  const fit = readFit(item.fit.axes);
  const room = roomFor(item);
  const eaten = birdsFor(item);

  return (
    <li
      className={extraLine ? 'suggestion-row suggestion-row--extra' : 'suggestion-row'}
      style={{ top }}
      tabIndex={stop}
      aria-posinset={index + 1}
      aria-setsize={setsize}
      data-index={index}
    >
      <button
        type="button"
        className="suggestion-row__name"
        tabIndex={stop}
        aria-label={`Informationen zu ${item.canonical_name}`}
        onClick={() => onShowInfo(item.taxon_id, item.canonical_name, item.flower_colour)}
      >
        {item.canonical_name}
      </button>
      <span className="suggestion-row__traits">
        <ColourMark item={item} />
        <MonthStrip start={item.flowering_start_month} end={item.flowering_end_month} />
        <InsectCount item={item} />
        {fit !== null ? (
          <span className={`suggestion-row__fit suggestion-row__fit--${fit.band}`} title={fit.full}>
            <span aria-hidden="true">{fit.short}</span>
            <span className="sr-only">{fit.spoken}</span>
          </span>
        ) : null}
      </span>
      {room !== null || eaten !== null ? (
        <span className="suggestion-row__extra">
          {room !== null ? <span className="suggestion-row__space">{room}</span> : null}
          {eaten !== null ? <span className="suggestion-row__birds">{eaten}</span> : null}
        </span>
      ) : null}
      {/* Last in reading order, first line on screen. Pressed while its request
          runs it does nothing and keeps the focus, which `disabled` would throw
          to the page (doc 88, rule 11). */}
      <button
        type="button"
        className="suggestion-row__plant"
        tabIndex={stop}
        aria-label={`${item.canonical_name} pflanzen`}
        aria-disabled={busy || undefined}
        title="Pflanzen"
        onClick={() => {
          if (!busy) void onPlant(item.taxon_id, item.canonical_name);
        }}
      >
        +
      </button>
    </li>
  );
}
