import { useEffect, useState } from 'react';

/** How long a hint stays over the drawing before it fades. */
export const HINT_VISIBLE_MS = 7_000;

/**
 * What the armed tool expects of the next gesture, over the drawing — for seven
 * seconds. Always there, "Wähle eine Form und …" covered the top of the plan
 * for good (the owner, 2026-09-21: "vielleicht nach 7 Sekunden ausblenden").
 *
 * A new hint, from picking another tool, shows again and starts its own seven
 * seconds. The paragraph itself stays, so the live region reads each new hint
 * out; faded, it is hidden from the accessibility tree as from the eye.
 */
export function PlanHint({ text }: { text: string }) {
  // Which hint has had its time: the next one is shown without a reset.
  const [fadedFor, setFadedFor] = useState<string | null>(null);
  useEffect(() => {
    const timer = window.setTimeout(() => setFadedFor(text), HINT_VISIBLE_MS);
    return () => window.clearTimeout(timer);
  }, [text]);
  const faded = fadedFor === text;
  return (
    <p className={faded ? 'plan-hint plan-hint--faded' : 'plan-hint'} aria-live="polite">
      {text}
    </p>
  );
}
