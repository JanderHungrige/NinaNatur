import { SYMBOLS } from './generated/symbols';

/**
 * His patterns, masks and ramps (doc 97), read by the browser's own parser:
 * about a thousand elements, which React would otherwise build one at a time
 * every time a plan mounts. The markup is generated from his pinned file and
 * holds nothing but ids, numbers, colours and this bundle's own image URLs —
 * the converter refuses anything else — so there is nothing in it to escape.
 */
export function DraftSketchDefs() {
  return <g dangerouslySetInnerHTML={{ __html: SYMBOLS }} />;
}
