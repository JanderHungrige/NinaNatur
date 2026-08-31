interface Props {
  /** Who is signed in, if anyone. */
  username: string | null;
  onSignIn: () => void;
  onSignUp: () => void;
  onSignOut: () => void;
  /** The arrow and its note only belong on the front door. */
  inviting: boolean;
  busy: boolean;
}

/**
 * Signing in, where sites put it.
 *
 * It used to be a panel in the middle of the landing page, between two ways of
 * making a garden — which is not where anybody looks for it, and it read as a
 * third thing to decide before starting.
 */
export function AccountBar({
  username,
  onSignIn,
  onSignUp,
  onSignOut,
  inviting,
  busy,
}: Props) {
  if (username !== null) {
    return (
      <div className="account-bar">
        <span className="account-bar__who">Angemeldet als {username}</span>
        <button type="button" className="link-button" disabled={busy} onClick={onSignOut}>
          Abmelden
        </button>
      </div>
    );
  }

  return (
    <div className="account-bar">
      {inviting && (
        <p className="account-bar__note" id="signup-note">
          {/* The truth of it: the share token already works, and it is a link
              somebody has to not lose. */}
          Ein Konto ist nicht nötig — aber es hält deine Gärten zusammen, auch
          wenn du den Link verlierst.
          {/* Decoration. The sentence above carries the whole meaning, which is
              why the arrow is hidden rather than described. */}
          <svg className="account-bar__arrow" viewBox="0 0 80 40" aria-hidden="true">
            <path
              d="M4 8 C 30 4, 52 10, 66 26"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            <path
              d="M60 27 L 68 28 L 64 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </p>
      )}
      <button type="button" className="link-button" disabled={busy} onClick={onSignIn}>
        Anmelden
      </button>
      <button
        type="button"
        className="account-bar__signup"
        disabled={busy}
        aria-describedby={inviting ? 'signup-note' : undefined}
        onClick={onSignUp}
      >
        Konto anlegen
      </button>
    </div>
  );
}
