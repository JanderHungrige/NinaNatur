import { useState } from 'react';

import {
  ATTRIBUTION,
  ATTRIBUTION_URL,
  type Imagery,
  type LatLon,
  type MapView,
  MAX_ZOOM,
  MIN_ZOOM,
  pixelToLatLon,
} from '../map/tiles';
import { useMapSurface } from '../map/useMapSurface';
import { MapPickerActions } from './MapPickerActions';
import { MapSurface } from './MapSurface';
import { Working } from './Working';

export interface Place {
  name: string;
  lat: number;
  lon: number;
}

export interface MapSelection {
  name: string;
  outline: LatLon[];
  neighbourhood: string;
}

interface Props {
  /** A promise, where there is one, keeps the button at "Wird angelegt…" until it settles. */
  onCreate: (selection: MapSelection) => Promise<void> | void;
  busy: boolean;
  search: (query: string) => Promise<Place[]>;
  /** Which state's orthophotos may be shown here, if any. */
  findImagery?: ((lat: number, lon: number) => Promise<Imagery | null>) | undefined;
  /** Overrides the measured size; tests pass it because jsdom lays nothing out. */
  size?: { widthPx: number; heightPx: number } | undefined;
}

const NEIGHBOURHOODS: Array<[string, string]> = [
  ['detached', 'Einfamilienhäuser (~7 m)'],
  ['terrace', 'Reihenhäuser (~9 m)'],
  ['apartment', 'Mehrfamilienhäuser (~14 m)'],
];

/** What the map is drawn at until the surface has been measured. */
const DEFAULT_SIZE = { widthPx: 640, heightPx: 400 };
const START_ZOOM = 18;

/**
 * Finding a garden on the map and outlining it.
 *
 * The map is OpenStreetMap's rendered tiles rather than aerial imagery: it
 * already shows buildings and roads, it is open, and it needed no licence
 * research to start. Using it carries obligations, and the visible attribution
 * below is one of them — it is a condition of use, not a footer.
 *
 * The map is drawn by `MapSurface`, and how big it is and how it is dragged
 * belong to `useMapSurface`: its size is measured rather than assumed, because
 * everything on it is drawn in that box (doc 31, B1).
 */
export function MapPicker({ onCreate, busy, search, findImagery, size }: Props) {
  const [query, setQuery] = useState('');
  const [places, setPlaces] = useState<Place[] | null>(null);
  /** Nominatim is a free service and answers when it can: say it is asked. */
  const [searching, setSearching] = useState(false);
  const [creating, setCreating] = useState(false);
  const [centre, setCentre] = useState<Place | null>(null);
  /**
   * Where the map is looking, which is not the same as which address was found.
   *
   * An allotment usually has no address of its own, so the one you can search
   * for is a street away from the plot you mean. Holding this apart from
   * `centre` is what lets the map be moved to the plot while the found address
   * stays the thing that was searched for.
   */
  const [look, setLook] = useState<{ lat: number; lon: number; zoom: number } | null>(
    null,
  );
  const [outline, setOutline] = useState<LatLon[]>([]);
  const [neighbourhood, setNeighbourhood] = useState('detached');
  const [problem, setProblem] = useState<string | null>(null);
  /** Said next to the search, not next to the create button: it is about the
   *  address that was just picked, and `problem` lives at the far end of the
   *  panel where nobody looks after choosing one. */
  const [moved, setMoved] = useState<string | null>(null);
  const [imagery, setImagery] = useState<Imagery | null>(null);
  const [aerial, setAerial] = useState(false);

  // The corners do not move with a drag: they are stored as coordinates, so
  // they stay on the ground while the view slides underneath.
  const surface = useMapSurface({
    fallback: DEFAULT_SIZE,
    size,
    shown: centre !== null,
    look,
    onLook: (at) => setLook((current) => (current === null ? current : { ...current, ...at })),
    onZoom: (by) => zoomBy(by),
  });
  const view: MapView = look === null
    ? { lat: 0, lon: 0, zoom: START_ZOOM, ...surface.box }
    : { ...look, ...surface.box };

  const find = () => {
    // Only when asked. A request per keystroke is how one gets blocked by a
    // free community service, deservedly.
    const q = query.trim();
    if (q === '' || searching) return;
    setSearching(true);
    void search(q)
      .catch((): Place[] => [])
      .then((found) => {
        setPlaces(found);
        setSearching(false);
      });
  };

  /** Look at a place that was found. */
  const goTo = (place: Place) => {
    // The corners belong to the address they were set on. Said, not silently
    // dropped: a drawing that vanishes without a word looks like a bug.
    if (outline.length > 0 && centre !== null && (
      centre.lat !== place.lat || centre.lon !== place.lon
    )) {
      setOutline([]);
      setMoved('Die Ecken gehörten zur alten Adresse und wurden entfernt.');
    } else {
      setMoved(null);
    }
    setCentre(place);
    setLook({ lat: place.lat, lon: place.lon, zoom: START_ZOOM });
    // Asked per place, because the licences are per Bundesland.
    void findImagery?.(place.lat, place.lon).then(setImagery).catch(() => setImagery(null));
  };

  const zoomBy = (by: number) => {
    setLook((current) =>
      current === null
        ? current
        : { ...current, zoom: Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, current.zoom + by)) },
    );
  };

  const addCorner = (event: React.MouseEvent<HTMLDivElement>) => {
    // The click a browser sends at the end of a drag belongs to the drag.
    if (surface.dragged() || centre === null) return;
    const rect = surface.ref.current?.getBoundingClientRect();
    const at = { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) };
    setOutline((current) => [...current, pixelToLatLon(at, view)]);
    setProblem(null);
  };

  const create = () => {
    if (outline.length < 3) {
      setProblem('Ein Garten braucht mindestens drei Ecken.');
      return;
    }
    setCreating(true);
    void Promise.resolve(
      onCreate({ name: centre?.name.split(',')[0] ?? 'Mein Garten', outline, neighbourhood }),
    ).finally(() => setCreating(false));
  };

  return (
    <section className="panel map-picker" aria-labelledby="map-heading">
      <h2 id="map-heading">Garten auf der Karte finden</h2>

      <label htmlFor="map-query">Adresse</label>
      <input
        id="map-query"
        type="text"
        value={query}
        disabled={busy}
        placeholder="z. B. Hauptstraße 1, Potsdam"
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') find();
        }}
      />
      {/* aria-disabled while it searches, not disabled: a button disabled
          under the keyboard throws its focus to the page (review). */}
      <button type="button" onClick={find} disabled={busy} aria-disabled={searching || undefined}>
        {searching ? <Working label="Suche…" /> : 'Suchen'}
      </button>

      {/* From the start, not only once the map appears: the address results are
          OpenStreetMap data too. Attribution is a condition of use for the data
          and is named again by the tile usage policy — the same rule that makes
          the Wikipedia credit part of the species panel's content. */}
      <p className="hint map-picker__attribution">
        Adressen und Karte:{' '}
        <a href={ATTRIBUTION_URL} target="_blank" rel="noreferrer noopener">
          {ATTRIBUTION}
        </a>
        {/* The imagery's own credit, shown whenever the imagery is: DL-DE/BY
            and CC-BY both require the named credit, so a photo without it is a
            photo used outside its licence. */}
        {aerial && imagery !== null && <> · Luftbild: {imagery.attribution}</>}
      </p>

      {places !== null && places.length === 0 && (
        <p className="hint">Dazu haben wir nichts gefunden.</p>
      )}
      {moved !== null && (
        <p className="hint" role="status">
          {moved}
        </p>
      )}
      {/* Shown whenever there are results, not only before one is picked. It
          used to be hidden as soon as a centre existed, so searching again
          updated a list nobody could see — and there was no way back to a
          different address. */}
      {places !== null && places.length > 0 && (
        <ul className="map-picker__places">
          {places.map((p) => (
            <li key={`${p.lat},${p.lon}`}>
              <button
                type="button"
                className="link-button"
                onClick={() => goTo(p)}
              >
                {p.name}
              </button>
            </li>
          ))}
        </ul>
      )}

      {centre !== null && (
        <>
          <p className="hint">
            Tippe oder klicke die Ecken deines Grundstücks. Was im Umkreis von 50 m
            steht und hoch genug ist, um Schatten bis zu dir zu werfen, wird mit
            übernommen. Mit dem <strong>Finger</strong> — am Rechner mit der{' '}
            <strong>rechten Maustaste</strong> — verschiebst du die Karte, nützlich,
            wenn dein Grundstück keine eigene Adresse hat.
          </p>

          <MapSurface
            surface={surface}
            view={view}
            outline={outline}
            imagery={imagery}
            aerial={aerial}
            busy={busy}
            zoom={look?.zoom ?? START_ZOOM}
            onZoom={zoomBy}
            onAddCorner={addCorner}
            size={size}
            height={DEFAULT_SIZE.heightPx}
          />

          {imagery !== null && (
            <label className="map-picker__toggle">
              <input
                type="checkbox"
                checked={aerial}
                disabled={busy}
                onChange={(e) => setAerial(e.target.checked)}
              />
              Luftbild statt Karte ({imagery.attribution})
            </label>
          )}

          <label htmlFor="map-neighbourhood">Nachbarbebauung</label>
          <select
            id="map-neighbourhood"
            value={neighbourhood}
            disabled={busy}
            onChange={(e) => setNeighbourhood(e.target.value)}
          >
            {NEIGHBOURHOODS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <p className="hint">
            OpenStreetMap kennt für die allermeisten Wohnhäuser keine Höhe. Diese
            eine Angabe füllt sie — einzelne Gebäude kannst du danach im Plan
            korrigieren.
          </p>

          <MapPickerActions
            points={outline.length}
            busy={busy}
            creating={creating}
            onUndo={() => setOutline((c) => c.slice(0, -1))}
            onCreate={create}
            problem={problem}
          />
        </>
      )}
    </section>
  );
}
