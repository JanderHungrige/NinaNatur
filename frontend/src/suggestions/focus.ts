/*
 * Where the keyboard's focus is, for lists whose rows come and go (doc 90).
 */

/** Whether the focus has fallen to the page: nothing, the body, or a node that
 *  is no longer in the document. */
export function focusLost(): boolean {
  const active = document.activeElement;
  return active === null || active === document.body || !active.isConnected;
}

/**
 * Whether the focus is inside `element` right now.
 *
 * Read while rendering, before the commit that may remove the node holding the
 * focus: once it is removed the focus is on the page, and nothing says where it
 * had been. By the time any effect runs — its cleanup included — it is too late.
 */
export function holdsFocus(element: HTMLElement | null): boolean {
  const active = document.activeElement;
  return element !== null && active !== null && element.contains(active);
}
