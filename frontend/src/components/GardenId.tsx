import { useState } from 'react';

interface Props {
  token: string;
  name: string;
  /** Rounded to 0.1° before it was ever stored — about 11 km. */
  latitude: number;
  longitude: number;
}

type CopyState = 'idle' | 'copied' | 'failed';

/**
 * The garden's id, where the person using it can see it.
 *
 * Until Wave 9 brings accounts this token is the only way back to a garden, so
 * it cannot be something a user has to know to look for in the address bar.
 *
 * It is also a **credential, not a row number**: whoever holds it can edit and
 * delete the garden. The wording says so, and the id itself stays in the URL
 * fragment — never a query parameter — so it reaches neither the server's access
 * log nor a third party's referrer header.
 */
export function GardenId({ token, name, latitude, longitude }: Props) {
  const [state, setState] = useState<CopyState>('idle');

  const copy = () => {
    // Needs a secure context and a permission, and can simply be absent. A
    // button that silently does nothing is worse than one that admits it.
    void navigator.clipboard
      ?.writeText(token)
      .then(() => setState('copied'))
      .catch(() => setState('failed'));
    if (navigator.clipboard === undefined) setState('failed');
  };

  return (
    // Folded away by default. It is a credential somebody needs once, when they
    // save the link — not something to look at while planning a garden, and it
    // was taking the top of the sidebar for a string nobody reads.
    <details className="panel garden-id">
      <summary className="garden-id__summary">{name} — ID und Infos</summary>
      <div className="garden-id__row">
        {/* Selectable text, so it stays usable when the copy button cannot. */}
        <code className="garden-id__token">{token}</code>
        <button type="button" onClick={copy}>
          ID kopieren
        </button>
      </div>
      <dl className="garden-id__facts">
        <dt>Standort</dt>
        <dd>
          {latitude.toFixed(1).replace('.', ',')}° N, {longitude.toFixed(1).replace('.', ',')}° O
        </dd>
      </dl>
      <p className="hint">
        Der Standort ist auf 0,1° gerundet gespeichert — rund 11 km, für den
        Sonnenstand genau genug und zu grob, um einen Garten zu finden.
      </p>
      <p className="hint">
        Mit dieser ID kommst du wieder zu diesem Garten — bewahre sie auf. Wer
        sie hat, kann deinen Garten ändern.
        {state === 'copied' && ' Kopiert.'}
        {state === 'failed' && ' Konnte nicht kopieren — markiere die ID und kopiere sie selbst.'}
      </p>
    </details>
  );
}
