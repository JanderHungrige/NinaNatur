import { type RefObject, useLayoutEffect } from 'react';

/**
 * Everything outside one element made `inert` while `active`, and given back
 * afterwards (doc 91).
 *
 * `inert` is the trap: what is outside can neither take the focus nor be
 * reached by a screen reader, with no key to intercept. It walks up from the
 * element and marks each level's other children, so it holds wherever the
 * element sits. What was inert already stays inert, and `spared` stays live —
 * the toast is a live region, and an inert one would say nothing.
 */
export function useInertOutside(
  kept: RefObject<HTMLElement | null>,
  active: boolean,
  spared = '.status-toast',
): void {
  useLayoutEffect(() => {
    const element = kept.current;
    if (!active || element === null) return undefined;
    const made: Element[] = [];
    let node: HTMLElement = element;
    while (node !== document.body) {
      const parent = node.parentElement;
      if (parent === null) break;
      for (const sibling of Array.from(parent.children)) {
        if (sibling === node || sibling.hasAttribute('inert') || sibling.matches(`script, ${spared}`)) continue;
        sibling.setAttribute('inert', '');
        made.push(sibling);
      }
      node = parent;
    }
    return () => {
      for (const sibling of made) sibling.removeAttribute('inert');
    };
  }, [kept, active, spared]);
}
