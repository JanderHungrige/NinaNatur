import type { GardenOut } from '../api/client';
import { ATTRIBUTION, ATTRIBUTION_URL } from '../map/tiles';
import { ROOFED } from '../roofs';
import { usePlanTheme } from '../themes/context';

/**
 * Whether the plan draws anything of OpenStreetMap's: a street, or a building
 * whose height, roof or eaves were not the gardener's. The server asks the same
 * question of the same fields for the garden's credits
 * (`ninanatur/garden/credits.py`, `from_the_map`), because nothing records
 * where an outline came from — a house drawn by hand is the gardener's in all
 * three, and a survey replaces a map house's height and roof, never its outline.
 */
export function drawsOpenStreetMap(garden: Pick<GardenOut, 'obstacles'>): boolean {
  return garden.obstacles.some((o) => o.kind === 'street' || (ROOFED.has(o.kind) && (
    o.height_source !== 'user' || o.roof_source === 'osm' || o.eaves_source === 'osm_levels')));
}

interface Props {
  /** The garden drawn: whether any of it is OpenStreetMap's decides the map's line. */
  garden: Pick<GardenOut, 'obstacles'>;
}

/**
 * The plan's captions, beneath it rather than on the drawing: in full, one
 * would cover a third of a phone's plan (doc 98).
 *
 * Whose drawing style the plan is in, in the words its author agreed to
 * (doc 97; THIRD_PARTY.md) — nothing for a theme of our own. And whose map
 * (2026-09-21): OpenStreetMap's streets and house outlines are drawn here, and
 * ODbL asks for the credit where they are shown, linked as its attribution
 * guideline asks.
 */
export function PlanCredit({ garden }: Props) {
  const { credit } = usePlanTheme();
  return (
    <>
      {credit === undefined ? null : <p className="plan-credit">{credit}</p>}
      {drawsOpenStreetMap(garden) ? (
        <p className="plan-credit">
          Karte:{' '}
          <a href={ATTRIBUTION_URL} target="_blank" rel="noreferrer noopener">{ATTRIBUTION}</a>
        </p>
      ) : null}
    </>
  );
}
