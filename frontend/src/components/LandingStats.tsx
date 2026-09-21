import type { StatsOut } from '../api/client';

function de(n: number): string {
  return n.toLocaleString('de-DE');
}

const LABELS = [
  'Arten im Katalog',
  'davon mit vollem Standortprofil',
  'erfasste Beziehungen zu heimischen Tieren',
] as const;

/**
 * The catalogue's figures on the front door, or the room they will take.
 *
 * The figures come from the API. Wave 1 wrote "3.087 Arten" into its HTML by
 * hand, and it was wrong the first time the catalogue was rebuilt: a page that
 * states a number is making a claim.
 *
 * While they are on their way the block stands already, its labels written and
 * its figures held by blanks of a figure's size, so the forms under the hero do
 * not jump down when the numbers land. The blanks are hidden from assistive
 * technology — a label with no value says nothing. If the catalogue does not
 * answer, the block goes: a front door with blanks forever is worse than one
 * without figures.
 */
export function LandingStats({ stats }: { stats: StatsOut | null | undefined }) {
  if (stats === null) return null;
  if (stats === undefined) {
    return (
      <dl className="landing__stats" aria-hidden="true" data-pending="">
        {LABELS.map((label) => (
          <div key={label} className="stat">
            <dt>{label}</dt>
            {/* A figure's width in a figure's font, drawn as a blank. */}
            <dd className="stat__pending">00.000</dd>
          </div>
        ))}
      </dl>
    );
  }
  const figures = [stats.species, stats.species_with_full_site_profile, stats.animal_partnerships];
  return (
    <dl className="landing__stats">
      {LABELS.map((label, index) => (
        <div key={label} className="stat">
          <dt>{label}</dt>
          <dd>{de(figures[index]!)}</dd>
        </div>
      ))}
    </dl>
  );
}
