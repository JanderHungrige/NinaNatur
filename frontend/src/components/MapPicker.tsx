import { useEffect, useRef, useState } from 'react';

import {
  ATTRIBUTION,
  type Imagery,
  imageryUrl,
  ATTRIBUTION_URL,
  MAX_ZOOM,
  MIN_ZOOM,
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
  const [panning, setPanning] = useState(false);
  const panFrom = useRef<{ x: number; y: number; lat: number; lon: number } | null>(null);
  const [outline, setOutline] = useState<LatLon[]>([]);
  const [neighbourhood, setNeighbourhood] = useState('detached');
  const [problem, setProblem] = useState<string | null>(null);
  /** Said next to the search, not next to the create button: it is about the
   *  address that was just picked, and `problem` lives at the far end of the
   *  panel where nobody looks after choosing one. */
  const [moved, setMoved] = useState<string | null>(null);
  const [imagery, setImagery] = useState<Imagery | null>(null);
  const [aerial, setAerial] = useState(false);
  const surface = useRef<HTMLDivElement | null>(null);

  const box = size ?? DEFAULT_SIZE;
  const view: MapView = look === null
    ? { lat: 0, lon: 0, zoom: START_ZOOM, ...box }
    : { ...look, ...box };

  const find = () => {
    // Only when asked. A request per keystroke is how one gets blocked by a
    // free community service, deservedly.
    const q = query.trim();
    if (q === '') return;
    void search(q).then(setPlaces).catch(() => setPlaces([]));
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

  /**
   * Right-drag moves the map.
   *
   * The right button because the left one is already how a corner is set, and
   * asking somebody to put the drawing tool down before moving the paper is
   * the sort of mode this picker has managed without.
   *
   * The corners do not move with it: they are stored as coordinates, so they
   * stay on the ground while the view slides underneath.
   */
  const grabMap = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.button !== 2 || look === null) return;
    event.preventDefault();
    panFrom.current = { x: event.clientX, y: event.clientY, lat: look.lat, lon: look.lon };
    setPanning(true);
  };

  useEffect(() => {
    if (!panning) return undefined;
    const onMove = (event: PointerEvent) => {
      const from = panFrom.current;
      if (from === null) return;
      // Through the projection rather than by scaling degrees: a degree of
      // longitude is not a degree of latitude, and at 52° it is not close.
      setLook((current) => {
        if (current === null) return current;
        const at: MapView = { ...current, lat: from.lat, lon: from.lon, ...box };
        const moved = pixelToLatLon(
          {
            x: box.widthPx / 2 - (event.clientX - from.x),
            y: box.heightPx / 2 - (event.clientY - from.y),
          },
          at,
        );
        return { ...current, lat: moved.lat, lon: moved.lon };
      });
    };
    const onUp = () => {
      panFrom.current = null;
      setPanning(false);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp);
    return () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
    };
  }, [panning, box.widthPx, box.heightPx]);

  const zoomBy = (by: number) => {
    setLook((current) =>
      current === null
        ? current
        : { ...current, zoom: Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, current.zoom + by)) },
    );
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
            Klicke die Ecken deines Grundstücks. Was im Umkreis von 50 m steht und
            hoch genug ist, um Schatten bis zu dir zu werfen, wird mit übernommen.
            Mit der <strong>rechten Maustaste</strong> verschiebst du die Karte —
            nützlich, wenn dein Grundstück keine eigene Adresse hat.
          </p>

          <div className="map-picker__zoom">
            <button
              type="button"
              aria-label="Herauszoomen"
              disabled={busy || (look?.zoom ?? START_ZOOM) <= MIN_ZOOM}
              onClick={() => zoomBy(-1)}
            >
              −
            </button>
            <button
              type="button"
              aria-label="Hineinzoomen"
              disabled={busy || (look?.zoom ?? START_ZOOM) >= MAX_ZOOM}
              onClick={() => zoomBy(1)}
            >
              +
            </button>
          </div>

          <div
            ref={surface}
            data-testid="map-surface"
            className="map-picker__surface"
            style={{ width: box.widthPx, height: box.heightPx }}
            onClick={addCorner}
            onPointerDown={grabMap}
            // Otherwise the browser's own menu opens in the middle of a pan.
            onContextMenu={(event) => event.preventDefault()}
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
