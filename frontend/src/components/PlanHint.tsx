import { type RefObject, useEffect, useRef, useState } from 'react';

/** How long a hint stays over the drawing before it fades. */
export const HINT_VISIBLE_MS = 7_000;

/**
 * What the armed tool expects of the next gesture, over the drawing — for seven
 * seconds. Always there, "Wähle eine Form und …" covered the top of the plan
 * for good (the owner, 2026-09-21: "vielleicht nach 7 Sekunden ausblenden").
 *
 * Every change of hint shows it again for seven seconds of its own, a hint
 * that comes back included: drawing a shape puts the tool down, and the select
 * hint then says the next step. The seven seconds count only while it can be
 * seen — the phone's raised sheet, the plan's own message and a background tab
 * hide it, and a hint that ran out behind them was never read. The paragraph itself stays, so
 * the live region reads each new hint out; faded, it is hidden from the
 * accessibility tree as from the eye.
 */
export function PlanHint({ text }: { text: string }) {
  const ref = useRef<HTMLParagraphElement>(null);
  const seen = useSeen(ref);
  const [shown, setShown] = useState({ text, faded: false });
  if (shown.text !== text) setShown({ text, faded: false });
  const faded = shown.text === text && shown.faded;
  useEffect(() => {
    if (!seen || faded) return undefined;
    const timer = window.setTimeout(
      () => setShown((now) => (now.text === text ? { text, faded: true } : now)),
      HINT_VISIBLE_MS,
    );
    return () => window.clearTimeout(timer);
  }, [text, seen, faded]);
  return (
    <p ref={ref} className={faded ? 'plan-hint plan-hint--faded' : 'plan-hint'} aria-live="polite">
      {text}
    </p>
  );
}

/** Whether the element is on screen: not `display: none`, not scrolled away,
 *  and on a tab that is showing — an observer counts a hidden tab's hint as in
 *  view, and a garden opened in a background tab lost its hint unread (review,
 *  2026-09-21). Seen where the browser cannot say, so a hint is never held
 *  back for ever. */
function useSeen(ref: RefObject<HTMLElement | null>): boolean {
  const [inView, setInView] = useState(true);
  const [showing, setShowing] = useState(() => document.visibilityState !== 'hidden');
  useEffect(() => {
    const element = ref.current;
    if (element === null || typeof IntersectionObserver === 'undefined') return undefined;
    const observer = new IntersectionObserver((entries) => {
      const last = entries[entries.length - 1];
      if (last !== undefined) setInView(last.isIntersecting);
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);
  useEffect(() => {
    const changed = () => setShowing(document.visibilityState !== 'hidden');
    document.addEventListener('visibilitychange', changed);
    return () => document.removeEventListener('visibilitychange', changed);
  }, []);
  return inView && showing;
}
