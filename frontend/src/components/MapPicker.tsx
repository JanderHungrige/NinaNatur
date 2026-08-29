import { useRef, useState } from 'react';

import {
  ATTRIBUTION,
  type Imagery,
  imageryUrl,
  ATTRIBUTION_URL,
  type LatLon,
  type MapView,
  latLonToPixel,
  pixelToLatLon,
  tileUrl,
  tilesFor,
} from '../map/tiles';

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
  onCreate: (selection: MapSelection) => void;
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

const DEFAULT_SIZE = { widthPx: 640, heightPx: 400 };
const START_ZOOM = 18;

/**
 * Finding a garden on the map and outlining it.
 *
 * The map is OpenStreetMap's rendered tiles rather than aerial imagery: it
 * already shows buildings and roads, it is open, and it needed no licence
 * research to start. Using it carries obligations, and the visible attribution
 * below is one of them — it is a condition of use, not a footer.
 */
export function MapPicker({ onCreate, busy, search, findImagery, size }: Props) {
  const [query, setQuery] = useState('');
  const [places, setPlaces] = useState<Place[] | null>(null);
  const [centre, setCentre] = useState<Place | null>(null);
  const [outline, setOutline] = useState<LatLon[]>([]);
  const [neighbourhood, setNeighbourhood] = useState('detached');
  const [problem, setProblem] = useState<string | null>(null);
  const [imagery, setImagery] = useState<Imagery | null>(null);
  const [aerial, setAerial] = useState(false);
  const surface = useRef<HTMLDivElement | null>(null);

  const box = size ?? DEFAULT_SIZE;
  const view: MapView = centre === null
    ? { lat: 0, lon: 0, zoom: START_ZOOM, ...box }
    : { lat: centre.lat, lon: centre.lon, zoom: START_ZOOM, ...box };

  const find = () => {
    // Only when asked. A request per keystroke is how one gets blocked by a
    // free community service, deservedly.
    const q = query.trim();
    if (q === '') return;
    void search(q).then(setPlaces).catch(() => setPlaces([]));
  };

  const addCorner = (event: React.MouseEvent<HTMLDivElement>) => {
    if (centre === null) return;
    const rect = surface.current?.getBoundingClientRect();
    const at = { x: event.clientX - (rect?.left ?? 0), y: event.clientY - (rect?.top ?? 0) };
    setOutline((current) => [...current, pixelToLatLon(at, view)]);
    setProblem(null);
  };

  const create = () => {
    if (outline.length < 3) {
      setProblem('Ein Garten braucht mindestens drei Ecken.');
      return;
    }
    onCreate({ name: centre?.name.split(',')[0] ?? 'Mein Garten', outline, neighbourhood });
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
      <button type="button" onClick={find} disabled={busy}>
        Suchen
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
      {places !== null && places.length > 0 && centre === null && (
        <ul className="map-picker__places">
          {places.map((p) => (
            <li key={`${p.lat},${p.lon}`}>
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setCentre(p);
                  // Asked per place, because the licences are per Bundesland.
                  void findImagery?.(p.lat, p.lon).then(setImagery).catch(() => setImagery(null));
                }}
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
            Klicke die Ecken deines Grundstücks. Was im Umkreis von 50 m steht und
            hoch genug ist, um Schatten bis zu dir zu werfen, wird mit übernommen.
          </p>

          <div
            ref={surface}
            data-testid="map-surface"
            className="map-picker__surface"
            style={{ width: box.widthPx, height: box.heightPx }}
            onClick={addCorner}
          >
            {aerial && imagery !== null ? (
              <img
                data-testid="map-aerial"
                className="map-picker__aerial"
                src={imageryUrl(imagery, view)}
                alt=""
                width={box.widthPx}
                height={box.heightPx}
              />
            ) : (
            <div data-testid="map-tiles" className="map-picker__tiles">
              {tilesFor(view).map((tile) => (
                <img
                  key={`${tile.z}/${tile.x}/${tile.y}`}
                  src={tileUrl(tile)}
                  alt=""
                  width={256}
                  height={256}
                  loading="lazy"
                  style={{ left: tile.left, top: tile.top }}
                />
              ))}
            </div>
            )}
            <svg className="map-picker__outline" viewBox={`0 0 ${box.widthPx} ${box.heightPx}`}>
              {outline.length > 1 && (
                <polygon
                  points={outline
                    .map((p) => {
                      const px = latLonToPixel(p, view);
                      return `${px.x},${px.y}`;
                    })
                    .join(' ')}
                />
              )}
              {outline.map((p) => {
                const px = latLonToPixel(p, view);
                return <circle key={`${p.lat},${p.lon}`} cx={px.x} cy={px.y} r={4} />;
              })}
            </svg>
          </div>

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

          <div className="map-picker__actions">
            <span className="hint">
              {outline.length} {outline.length === 1 ? 'Punkt' : 'Punkte'}
            </span>
            <button
              type="button"
              aria-label="Rückgängig"
              disabled={busy || outline.length === 0}
              onClick={() => setOutline((c) => c.slice(0, -1))}
            >
              ↶
            </button>
            <button type="button" onClick={create} disabled={busy}>
              Garten anlegen
            </button>
          </div>
          {problem !== null && (
            <p className="hint" role="alert">
              {problem}
            </p>
          )}
        </>
      )}
    </section>
  );
}
