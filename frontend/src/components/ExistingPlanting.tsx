import { useState } from 'react';

import { plantings as plantingCount } from '../plural';

interface Props {
  onAdd: (planting: { raw_name: string; quantity: number }) => void;
  /** How many plantings the catalogue could not name. */
  unidentified: number;
  busy: boolean;
}

/**
 * What already grows here.
 *
 * A garden is not empty when someone starts planning it, and the catalogue holds
 * 8,939 German species and no cultivars at all — so a name it cannot match is an
 * ordinary answer, not a mistake. The form says that before the user finds out
 * by being told they were wrong.
 */
export function ExistingPlanting({ onAdd, unidentified, busy }: Props) {
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('1');

  const submit = () => {
    const trimmed = name.trim();
    if (trimmed === '') return;
    onAdd({ raw_name: trimmed, quantity: Math.max(1, Number(quantity) || 1) });
    setName('');
    setQuantity('1');
  };

  return (
    <section className="panel existing-planting" aria-labelledby="existing-heading">
      <h2 id="existing-heading">Vorhandene Bepflanzung</h2>
      <p className="hint">
        Trage ein, was schon da ist — deutscher oder wissenschaftlicher Name. Du
        kannst eine Pflanze auch eintragen, wenn wir sie nicht kennen; sie steht
        dann in deinem Plan, zählt aber nicht in den Insektenwert.
      </p>

      <label htmlFor="existing-name">Pflanze</label>
      <input
        id="existing-name"
        type="text"
        value={name}
        disabled={busy}
        placeholder="z. B. Echte Schlüsselblume"
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') submit();
        }}
      />

      <label htmlFor="existing-quantity">Anzahl</label>
      <input
        id="existing-quantity"
        type="number"
        min="1"
        value={quantity}
        disabled={busy}
        onChange={(e) => setQuantity(e.target.value)}
      />

      <div className="existing-planting__actions">
        <button type="button" onClick={submit} disabled={busy}>
          Eintragen
        </button>
      </div>

      {unidentified > 0 && (
        <p className="hint">
          {plantingCount(unidentified)} konnten wir keiner Art zuordnen. Sie
          bleiben im Plan, gehen aber nicht in Insektenwert und Blühjahr ein —
          dort fehlen uns die Daten.
        </p>
      )}
    </section>
  );
}
