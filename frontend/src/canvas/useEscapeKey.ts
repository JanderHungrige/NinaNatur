import { useEffect } from 'react';

/** Input types that take a key press as something other than text. */
const NOT_TYPED = new Set(['checkbox', 'radio', 'range', 'color', 'file', 'button', 'submit', 'reset', 'image']);

/** Whether a key press lands in something being typed into. */
export function isTextEntry(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target instanceof HTMLTextAreaElement) return true;
  if (target instanceof HTMLInputElement) return !NOT_TYPED.has(target.type);
  // jsdom has no isContentEditable, so the attribute is read as well.
  const editable = target.getAttribute('contenteditable');
  return target.isContentEditable === true || (editable !== null && editable !== 'false');
}

/**
 * Escape, from anywhere except a text field (doc 88).
 *
 * Escape is the one way out of a drawing mode and a selection, and it listens
 * always (doc 49). Since the details show the selection, dropping it also takes
 * away the view the focus is in — so Escape typed into a name or a number
 * belongs to that field, and nothing half typed is lost with the view.
 */
export function useEscapeKey(onEscape: () => void): void {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || isTextEntry(event.target)) return;
      onEscape();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onEscape]);
}
