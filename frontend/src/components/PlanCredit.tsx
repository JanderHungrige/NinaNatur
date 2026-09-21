import type { GardenOut } from '../api/client';
import { ATTRIBUTION, ATTRIBUTION_URL } from '../map/tiles';
import { usePlanTheme } from '../themes/context';

/**
 * Whether the plan draws anything of OpenStreetMap's: a street, or an outline
 * the map import brought (`outline_source`, which only the server writes and
 * nothing changes). The server asks the same question for the garden's credits
 * (`ninanatur/garden/credits.py`, `from_the_map`). It used to be read off a
 * house's height, roof and eaves, and a map house the gardener had corrected
 * lost its credit while the plan still drew OpenStreetMap's outline.
 *
 * Or the land around the garden, where the plan draws any (doc 114) — which a
 * garden drawn by hand gets on its first shade rebuild, streets or none.
 */
export function drawsOpenStreetMap(garden: Pick<GardenOut, 'obstacles'>, landcover = false): boolean {
  return landcover || garden.obstacles.some((o) => o.kind === 'street' || o.outline_source === 'osm');
}

interface Props {
  /** The garden drawn: whether any of it is OpenStreetMap's decides the map's line. */
  garden: Pick<GardenOut, 'obstacles'>;
  /** Whether the plan draws OpenStreetMap's land around it (doc 114). */
  landcover?: boolean;
}

/**
 * The plan's captions, beneath it rather than on the drawing: in full, one
 * would cover a third of a phone's plan (doc 98).
 *
 * Whose drawing style the plan is in, in the words its author agreed to
 * (doc 97; THIRD_PARTY.md) — nothing for a theme of our own. And whose map
 * (2026-09-21): OpenStreetMap's streets, house outlines and land are drawn here, and
 * ODbL asks for the credit where they are shown, linked as its attribution
 * guideline asks.
 */
export function PlanCredit({ garden, landcover = false }: Props) {
  const { credit } = usePlanTheme();
  return (
    <>
      {credit === undefined ? null : <p className="plan-credit">{credit}</p>}
      {drawsOpenStreetMap(garden, landcover) ? (
        <p className="plan-credit">
          Karte:{' '}
          <a href={ATTRIBUTION_URL} target="_blank" rel="noreferrer noopener">{ATTRIBUTION}</a>
        </p>
      ) : null}
    </>
  );
}
