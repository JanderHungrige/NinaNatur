import { useId, useState } from 'react';

import { GardenSoil } from './GardenSoil';

interface Props {
  soilType: string | null;
  moisture: string | null;
  onSave: (soilType: string, moisture: string) => void;
  busy: boolean;
}

/** The words the element form uses for the same values. */
const SOIL_WORDS: Record<string, string> = {
  sand: 'sandig',
  loam: 'lehmig',
  clay: 'tonig',
  humus: 'humos',
};

const MOISTURE_WORDS: Record<string, string> = {
  dry: 'trocken',
  fresh: 'frisch',
  moist: 'feucht',
  wet: 'nass',
};

/**
 * The garden's soil as one line, once it has been said (doc 88).
 *
 * Doc 48 asks it once per garden, and the answer then stood in the sidebar as a
 * 448 px form for good. Answered, it is one line with the question behind
 * "ändern"; unanswered, it is the question itself.
 */
export function SoilLine({ soilType, moisture, onSave, busy }: Props) {
  const [open, setOpen] = useState(false);
  const questionId = useId();

  if (soilType === null || moisture === null) {
    return <GardenSoil soilType={soilType} moisture={moisture} onSave={onSave} busy={busy} />;
  }

  const answer = `${SOIL_WORDS[soilType] ?? soilType}, ${MOISTURE_WORDS[moisture] ?? moisture}`;

  return (
    <>
      <div className="soil-line">
        <p className="soil-line__value">
          Boden: <strong>{answer}</strong>
        </p>
        <button
          type="button"
          className="link-button"
          aria-label="Boden ändern"
          aria-expanded={open}
          aria-controls={open ? questionId : undefined}
          onClick={() => setOpen(!open)}
        >
          ändern
        </button>
      </div>
      {open ? (
        <div id={questionId}>
          <GardenSoil
            soilType={soilType}
            moisture={moisture}
            busy={busy}
            onSave={(soil, wet) => {
              onSave(soil, wet);
              setOpen(false);
            }}
          />
        </div>
      ) : null}
    </>
  );
}
