import type { ReactNode } from 'react';

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
}

/**
 * The one header, on the front door and in a garden (doc 87).
 *
 * In a garden it also carries what acts on the whole garden rather than on one
 * part of it: its name and id, undo, and the sun map over the plan.
 */
export function SiteHeader({ version, onHome, onFeedback, accountBar, busy, children }: Props) {
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
      <button type="button" className="header-link header-link--feedback" onClick={onFeedback}>
        Rückmeldung
      </button>
      <AccountBar {...accountBar} busy={busy} />
    </header>
  );
}
