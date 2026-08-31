import { useState } from 'react';

import type { OwnedGardens } from '../api/client';

interface Props {
  gardens: OwnedGardens['gardens'];
  onOpen: (token: string) => void;
  onDelete: (token: string) => void;
  busy: boolean;
}

/** "vor 3 Tagen" reads better than a timestamp for a list you skim. */
function when(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const days = Math.floor((Date.now() - then) / 86_400_000);
  if (days <= 0) return 'heute geändert';
  if (days === 1) return 'gestern geändert';
  if (days < 30) return `vor ${days} Tagen geändert`;
  const months = Math.floor(days / 30);
  return months === 1 ? 'vor einem Monat geändert' : `vor ${months} Monaten geändert`;
}

/**
 * The gardens this account has claimed.
 *
 * The endpoint has existed since Wave 9 and nothing displayed it — the account
 * kept the links and then never showed them, so the share token was still the
 * only way back in.
 */
export function MyGardens({ gardens, onOpen, onDelete, busy }: Props) {
  /** Which row is asking to be sure. Deleting a garden cannot be undone. */
  const [confirming, setConfirming] = useState<string | null>(null);

  return (
    <section className="panel my-gardens" aria-labelledby="my-gardens-heading">
      <h2 id="my-gardens-heading">Deine Gärten</h2>
      {gardens.length === 0 ? (
        <p className="hint">
          Noch keiner. Leg unten einen an — er wird diesem Konto zugeordnet.
        </p>
      ) : (
        <ul className="my-gardens__rows">
          {gardens.map((garden) => (
            <li key={garden.share_token} className="my-gardens__row">
              <button
                type="button"
                className="my-gardens__open"
                disabled={busy}
                onClick={() => onOpen(garden.share_token)}
              >
                <span className="my-gardens__name">{garden.name}</span>
                <span className="my-gardens__when">{when(garden.updated_at)}</span>
              </button>

              {confirming === garden.share_token ? (
                <span className="my-gardens__confirm" role="group" aria-label="Löschen bestätigen">
                  {/* Named rather than "Ja": a button that says what it does is
                      the difference between confirming and clicking on. */}
                  <button
                    type="button"
                    className="my-gardens__danger"
                    disabled={busy}
                    onClick={() => {
                      setConfirming(null);
                      onDelete(garden.share_token);
                    }}
                  >
                    Endgültig löschen
                  </button>
                  <button
                    type="button"
                    className="link-button"
                    disabled={busy}
                    onClick={() => setConfirming(null)}
                  >
                    Abbrechen
                  </button>
                </span>
              ) : (
                <button
                  type="button"
                  className="link-button my-gardens__delete"
                  disabled={busy}
                  aria-label={`${garden.name} löschen`}
                  onClick={() => setConfirming(garden.share_token)}
                >
                  Löschen
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
