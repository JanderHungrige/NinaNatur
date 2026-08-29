import { useState } from 'react';

interface Props {
  token: string;
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
export function GardenId({ token }: Props) {
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
    <section className="panel garden-id" aria-labelledby="garden-id-heading">
      <h2 id="garden-id-heading" className="sr-only">
        Garten-ID
      </h2>
      <div className="garden-id__row">
        {/* Selectable text, so it stays usable when the copy button cannot. */}
        <code className="garden-id__token">{token}</code>
        <button type="button" onClick={copy}>
          ID kopieren
        </button>
      </div>
      <p className="hint">
        Mit dieser ID kommst du wieder zu diesem Garten — bewahre sie auf. Wer
        sie hat, kann deinen Garten ändern.
        {state === 'copied' && ' Kopiert.'}
        {state === 'failed' && ' Konnte nicht kopieren — markiere die ID und kopiere sie selbst.'}
      </p>
    </section>
  );
}
