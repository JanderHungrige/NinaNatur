import { useState } from 'react';

interface Props {
  onCreate: (input: { name: string; latitude: number; longitude: number }) => Promise<void>;
  busy: boolean;
}

/** Creating a garden. A location is required — without one there is no sun path. */
export function NewGardenForm({ onCreate, busy }: Props) {
  const [name, setName] = useState('Mein Garten');
  const [latitude, setLatitude] = useState('52.5');
  const [longitude, setLongitude] = useState('13.4');

  return (
    <form
      className="panel"
      onSubmit={(event) => {
        event.preventDefault();
        void onCreate({
          name,
          latitude: Number.parseFloat(latitude),
          longitude: Number.parseFloat(longitude),
        });
      }}
    >
      <h2>Neuen Garten anlegen</h2>
      <p className="hint">
        Der Standort bestimmt den Sonnenstand. Er wird auf 0,1° gerundet gespeichert —
        rund 11&nbsp;km, für die Sonnengeometrie genau genug.
      </p>

      <label htmlFor="garden-name">Name</label>
      <input id="garden-name" value={name} onChange={(e) => setName(e.target.value)} required />

      <div className="row">
        <div>
          <label htmlFor="garden-lat">Breitengrad</label>
          <input
            id="garden-lat" type="number" step="0.0001" min="-90" max="90"
            value={latitude} onChange={(e) => setLatitude(e.target.value)} required
          />
        </div>
        <div>
          <label htmlFor="garden-lon">Längengrad</label>
          <input
            id="garden-lon" type="number" step="0.0001" min="-180" max="180"
            value={longitude} onChange={(e) => setLongitude(e.target.value)} required
          />
        </div>
      </div>

      <button type="submit" disabled={busy}>
        {busy ? 'Wird angelegt…' : 'Garten anlegen'}
      </button>
    </form>
  );
}
