import {
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
  useEffect,
  useId,
  useRef,
  useState,
} from 'react';

import { AccountBar } from './AccountBar';

/** What the site hands the header, on the front door and in a garden alike. */
export interface SiteProps {
  version: string | null;
  onHome: () => void;
  onFeedback: () => void;
  accountBar: {
    username: string | null;
    onSignIn: () => void;
    onSignUp: () => void;
    onSignOut: () => void;
    /** The arrow and its note only belong on the front door. */
    inviting: boolean;
  };
}

interface Props extends SiteProps {
  busy: boolean;
  /** The open garden's own controls, between the version and the feedback button. */
  children?: ReactNode;
  /** More of the garden's controls, which a narrow window keeps behind *Menü* (doc 91). */
  more?: ReactNode;
}

/**
 * The one header, on the front door and in a garden (doc 87).
 *
 * In a garden it also carries what acts on the whole garden rather than on one
 * part of it: its name and id, undo, and the sun map over the plan.
 *
 * On a narrow window a garden's header is one row (doc 91): the version, the
 * extra controls, feedback and the account wait behind *Menü*. The stylesheet
 * shows that button only there; everywhere else the menu's contents stand in
 * the row as they always did.
 */
export function SiteHeader({ version, onHome, onFeedback, accountBar, busy, children, more }: Props) {
  const menuId = useId();
  const [open, setOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);

  // A pointer going down anywhere but the menu and its button closes it.
  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event: Event) => {
      const target = event.target instanceof Node ? event.target : null;
      if (target !== null && (menu.current?.contains(target) || toggle.current?.contains(target))) return;
      setOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [open]);

  // Escape closes an open menu and stops there, so the plan's Escape never hears it.
  const onKey = (event: KeyboardEvent<HTMLElement>) => {
    if (!open || event.key !== 'Escape') return;
    event.preventDefault();
    event.stopPropagation();
    setOpen(false);
    toggle.current?.focus();
  };

  // Pressing anything in the menu does that thing, and the menu closes.
  const onMenuClick = (event: MouseEvent<HTMLDivElement>) => {
    if (event.target instanceof Element && event.target.closest('button, a') !== null) setOpen(false);
  };

  return (
    <header className="site-header">
      <button type="button" className="brand" onClick={onHome} aria-label="Zur Startseite">
        <svg className="brand__mark" viewBox="0 0 64 64" aria-hidden="true">
          <path className="mark__leaf" d="M32 58C32 40 40 26 56 20 56 40 46 54 32 58Z" />
          <path className="mark__leaf mark__leaf--alt" d="M32 58C32 40 24 26 8 20 8 40 18 54 32 58Z" />
          <path className="mark__stem" d="M32 58V30" />
          <path className="mark__letters" d="M14 24V8l12 16V8M38 24V8l12 16V8" />
        </svg>
        <span className="brand__name">NinaNatur</span>
      </button>
      {version !== null ? (
        <span className="badge" title="Version · Wave · Merges auf main">
          {version}
        </span>
      ) : null}
      {children}
      <button
        ref={toggle}
        type="button"
        className="header-link site-header__menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen(!open)}
        onKeyDown={onKey}
      >
        Menü
      </button>
      <div
        id={menuId}
        ref={menu}
        className="site-header__more"
        data-open={open}
        onClick={onMenuClick}
        onKeyDown={onKey}
      >
        {version !== null ? <p className="site-header__version">Version {version}</p> : null}
        {more}
        <button type="button" className="header-link header-link--feedback" onClick={onFeedback}>
          Rückmeldung
        </button>
        <AccountBar {...accountBar} busy={busy} />
      </div>
    </header>
  );
}
