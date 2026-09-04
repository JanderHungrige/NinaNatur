import { useState } from 'react';

import type { GardenOut } from '../api/client';
import { species } from '../plural';

type Bed = GardenOut['beds'][number];
type Planting = Bed['plantings'][number];

interface Props {
  bed: Bed;
  onRemove: (plantingId: number) => void;
  /** The same panel the suggestions open. Absent while nothing can show it. */
  onShowInfo?: ((taxonId: number, name: string) => void) | undefined;
  busy: boolean;
}

/** What to call a planting. The catalogue's name, or the gardener's own for a
 *  plant it could not identify. */
export function nameOf(planting: Planting): string {
  return planting.canonical_name ?? planting.raw_name ?? 'Unbenannt';
}

/**
 * What is standing in this bed, and how to take it out again.
 *
 * The plan says how full a bed looks and the suggestions say what could go in
 * it. Neither answered the plainest question — what did I plant here — and
 * there was no way to undo a planting short of deleting the bed with it.
 *
 * Removal asks first. A planting is a decision somebody made, sometimes weeks
 * ago, and the row it sits in is one keystroke from the row above it.
 */
export function BedPlantings({ bed, onRemove, onShowInfo, busy }: Props) {
  const [confirming, setConfirming] = useState<number | null>(null);
  const planted = bed.plantings;

  return (
    <section className="panel bed-plantings" aria-labelledby="planted-heading">
      <h2 id="planted-heading">In {bed.name}</h2>

      {planted.length === 0 ? (
        <p className="hint">
          Noch nichts gepflanzt. Wähle unten einen Vorschlag — oder trage oben
          ein, was schon da ist.
        </p>
      ) : (
        <>
          <p className="hint">{species(planted.length)} in diesem Beet.</p>
          <ul className="bed-plantings__rows">
            {planted.map((planting) => (
              <li key={planting.planting_id} className="bed-plantings__row">
                <span className="bed-plantings__name">
                  {nameOf(planting)}
                  {planting.quantity > 1 ? (
                    <span className="bed-plantings__count">
                      {' '}
                      × {planting.quantity}
                    </span>
                  ) : null}
                  {/* Said, not hidden: a plant the catalogue cannot name still
                      stands in the bed, but it counts for nothing in the
                      insect score, and the gardener should know which is
                      which. */}
                  {planting.taxon_id === null ? (
                    <span className="hint"> · nicht im Katalog</span>
                  ) : null}
                </span>

                <span className="bed-plantings__actions">
                  {planting.taxon_id !== null && onShowInfo !== undefined ? (
                    <button
                      type="button"
                      className="link-button"
                      onClick={() =>
                        onShowInfo(planting.taxon_id as number, nameOf(planting))
                      }
                    >
                      Info
                    </button>
                  ) : null}

                  {confirming === planting.planting_id ? (
                    <>
                      <button
                        type="button"
                        className="link-button link-button--warn"
                        disabled={busy}
                        onClick={() => {
                          setConfirming(null);
                          onRemove(planting.planting_id);
                        }}
                      >
                        Wirklich entfernen
                      </button>
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => setConfirming(null)}
                      >
                        Doch nicht
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className="link-button"
                      disabled={busy}
                      onClick={() => setConfirming(planting.planting_id)}
                    >
                      Entfernen
                    </button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
