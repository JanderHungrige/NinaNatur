import type {
  BloomPalette,
  ImprovementsOut,
  LightMap,
  NinaNaturClient,
  ScoreOut,
  Terrain,
  TimelineOut,
} from './api/client';

/** Where each of a garden's derived answers is shown. */
export interface DerivedSetters {
  timeline: (value: TimelineOut) => void;
  score: (value: ScoreOut) => void;
  improvements: (value: ImprovementsOut) => void;
  palette: (value: BloomPalette) => void;
  lightMap: (value: LightMap | null) => void;
  terrain: (value: Terrain | null) => void;
}

/** The part of the client they come from. */
export type DerivedSource = Pick<
  NinaNaturClient,
  'timeline' | 'score' | 'improvements' | 'bloom' | 'lightMap' | 'terrain'
>;

/**
 * Everything the server derives from a garden, asked for at once.
 *
 * Opening a garden used to await eight requests one after another, each a full
 * round trip through the proxy and none of them waiting on another's answer.
 * Asked together they cost the slowest of them rather than the sum. Each answer
 * is shown as it arrives, so a slow one delays only itself; a failed one costs
 * only itself too, and the returned promise still rejects so the caller can say
 * so.
 *
 * The same six are read on opening and after every change, which is why they
 * live in one place: anything fetched in one and not the other stays a version
 * behind until the next edit. The bloom colours and the sun map each fell into
 * that once — a garden opened from its link had neither until something was
 * edited.
 */
export async function fetchDerived(
  client: DerivedSource,
  token: string,
  weighted: boolean,
  show: DerivedSetters,
): Promise<void> {
  await Promise.all([
    client.timeline(token, weighted).then(show.timeline),
    client.score(token).then(show.score),
    // With the garden rather than on bed selection: the suggestions are the
    // point of the score, and hiding them until something is clicked buries it.
    client.improvements(token).then(show.improvements),
    client.bloom(token).then(show.palette),
    client.lightMap(token).then(show.lightMap),
    // The ground only changes when it is first fetched, on the recompute
    // button, so this is nearly always the same answer. Read anyway: otherwise
    // the map is right and the relief a version behind.
    client.terrain(token).then(show.terrain),
  ]);
}
