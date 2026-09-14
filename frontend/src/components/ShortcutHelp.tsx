import { Fragment, type KeyboardEvent, type SyntheticEvent, useEffect, useId, useRef } from 'react';

import { type Chord, SHORTCUTS } from '../workspace/shortcuts';

interface Props {
  open: boolean;
  onClose: () => void;
}

/** "Umschalt+F10 oder Kontextmenü", every key as a key. */
function Keys({ keys }: { keys: readonly Chord[] }) {
  return (
    <>
      {keys.map((chord, index) => (
        <Fragment key={chord.join('+')}>
          {index > 0 ? ' oder ' : null}
          {chord.map((key, at) => (
            <Fragment key={key}>
              {at > 0 ? '+' : null}
              <kbd>{key}</kbd>
            </Fragment>
          ))}
        </Fragment>
      ))}
    </>
  );
}

/**
 * The keyboard's shortcuts, as a modal dialog (doc 92).
 *
 * Native, so the browser holds the focus inside it and the page behind it
 * inert; jsdom has no `showModal`, so there it is merely open. No key pressed
 * in it reaches the page: the page's Escape would clear the selection, and its
 * Ctrl+Z take back a change nobody can see behind the help.
 */
export function ShortcutHelp({ open, onClose }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  const headingId = useId();

  useEffect(() => {
    const element = dialog.current;
    if (!open || element === null) return undefined;
    if (typeof element.showModal === 'function') element.showModal();
    else element.setAttribute('open', '');
    close.current?.focus();
    return () => {
      if (typeof element.close === 'function') element.close();
    };
  }, [open]);

  if (!open) return null;

  const onKeyDown = (event: KeyboardEvent<HTMLDialogElement>) => {
    event.stopPropagation();
    if (event.key !== 'Escape') return;
    event.preventDefault();
    onClose();
  };

  // A close the browser asks for by itself, such as a phone's back gesture.
  const onCancel = (event: SyntheticEvent<HTMLDialogElement>) => {
    event.preventDefault();
    onClose();
  };

  return (
    <dialog
      ref={dialog}
      className="shortcut-help"
      aria-labelledby={headingId}
      onKeyDown={onKeyDown}
      onCancel={onCancel}
    >
      <div className="shortcut-help__head">
        <h2 id={headingId}>Tastenkürzel</h2>
        <button ref={close} type="button" className="link-button" onClick={onClose}>
          Schließen
        </button>
      </div>
      <p className="hint">Auf einem Mac steht ⌘ für Strg. In einem Textfeld gehören die Tasten dem Feld.</p>
      {SHORTCUTS.map((group) => (
        <section key={group.heading}>
          <h3>{group.heading}</h3>
          <dl className="shortcut-help__list">
            {group.shortcuts.map((shortcut) => (
              <div key={shortcut.does}>
                <dt>
                  <Keys keys={shortcut.keys} />
                </dt>
                <dd>{shortcut.does}</dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </dialog>
  );
}
