import { useEffect, useState } from 'react';

const QUERY = '(prefers-reduced-motion: reduce)';

/**
 * Whether this visitor has asked their system for less movement.
 *
 * CSS can answer the same question, but only by hiding things. A `<video>`
 * behind `display: none` is still fetched and still decoded, so the one visitor
 * who asked for less would pay the most for it. This lets the component decide
 * not to render it at all.
 *
 * The listener stays subscribed: the setting can change while the page is open,
 * on macOS from the Accessibility pane, and a background that only obeys on
 * reload is not obeying.
 */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(matches);

  useEffect(() => {
    // Guarded because jsdom has no matchMedia unless a test provides one, and a
    // decorative background must not be what breaks an unrelated test.
    const query = window.matchMedia?.(QUERY);
    if (query === undefined) return;
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener('change', onChange);
    setReduced(query.matches);
    return () => query.removeEventListener('change', onChange);
  }, []);

  return reduced;
}

function matches(): boolean {
  return window.matchMedia?.(QUERY).matches ?? false;
}


/**
 * Whether this visitor has switched on their browser's data saver.
 *
 * Three megabytes is nothing on a desk and a real amount on a train. Someone
 * who has asked their browser to spend less is asking about exactly this kind
 * of file, and the page has a background either way.
 *
 * Read once rather than watched: unlike the motion setting, this one is not
 * something people toggle while looking at a page, and `connection` is absent
 * on Safari and Firefox entirely.
 */
export function prefersLessData(): boolean {
  const connection = (
    navigator as Navigator & { connection?: { saveData?: boolean } }
  ).connection;
  return connection?.saveData === true;
}
