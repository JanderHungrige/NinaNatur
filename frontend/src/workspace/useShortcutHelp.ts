import { useCallback, useEffect, useRef, useState } from 'react';

import { isTextEntry } from '../canvas/useEscapeKey';

/**
 * Back to where the focus was. When that can no longer take it — *Tastenkürzel*
 * behind a narrow window's *Menü*, which closed as it was chosen — to the button
 * that controls the region it stood in.
 */
function giveFocusBack(target: Element): void {
  if (!(target instanceof HTMLElement || target instanceof SVGElement) || !target.isConnected) return;
  target.focus();
  if (document.activeElement === target) return;
  for (let region = target.parentElement; region !== null; region = region.parentElement) {
    const id = region.id;
    if (id === '') continue;
    const toggle = Array.from(document.querySelectorAll<HTMLElement>('[aria-controls]')).find((element) =>
      (element.getAttribute('aria-controls') ?? '').split(/\s+/).includes(id),
    );
    if (toggle !== undefined) {
      toggle.focus();
      return;
    }
  }
}

/**
 * Whether the keyboard's shortcuts are showing (doc 92): open on `?`, and the
 * focus given back once they close.
 *
 * A `?` typed into a field is the field's, and one held with Ctrl, Cmd or Alt
 * is the browser's.
 */
export function useShortcutHelp(): { open: boolean; show: () => void; hide: () => void } {
  const [open, setOpen] = useState(false);
  const returnTo = useRef<Element | null>(null);

  const show = useCallback(() => {
    returnTo.current ??= document.activeElement;
    setOpen(true);
  }, []);
  const hide = useCallback(() => setOpen(false), []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== '?' || event.ctrlKey || event.metaKey || event.altKey) return;
      if (isTextEntry(event.target)) return;
      event.preventDefault();
      show();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [show]);

  // After the commit that closed it: the dialog has left the page by then, so
  // nothing outside it is blocked from taking the focus.
  useEffect(() => {
    if (open) return;
    const target = returnTo.current;
    returnTo.current = null;
    if (target !== null) giveFocusBack(target);
  }, [open]);

  return { open, show, hide };
}
