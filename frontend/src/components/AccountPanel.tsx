import { useState } from 'react';

export interface AccountInfo {
  username: string;
  email: string | null;
  recovery_note: string;
}

interface Props {
  account: AccountInfo | null;
  onRegister: (input: { username: string; password: string; email?: string }) => Promise<void>;
  onLogin: (input: { username: string; password: string }) => Promise<void>;
  onLogout: () => Promise<void>;
  busy: boolean;
}

/**
 * Mirrors the server's minimum. Told here rather than after a 422.
 *
 * Eight, not ten. Ten was arbitrary and felt like it; eight is the floor NIST
 * SP 800-63B sets for a user-chosen secret, and the same guidance says not to
 * impose composition rules on top — so there are none. What makes a password
 * strong is said as a hint, not enforced as a gate.
 */
const MIN_PASSWORD = 8;

/** Mirrors the server's `^[\w.-]+$`. */
const USERNAME_PATTERN = /^[\w.-]+$/;
const MIN_USERNAME = 3;

const USERNAME_RULE =
  'Mindestens 3 Zeichen. Buchstaben, Ziffern, Punkt, Unterstrich und Bindestrich.';

const PASSWORD_HINT =
  'Mindestens 8 Zeichen. Länger ist besser als komplizierter — und eine Mischung ' +
  'aus Groß- und Kleinbuchstaben, Ziffern und Sonderzeichen macht es zusätzlich sicherer.';

const NO_EMAIL_WARNING =
  'Ohne E-Mail-Adresse kann dein Passwort nicht zurückgesetzt werden. Vergisst du es, ist der Zugang verloren.';

/**
 * Registering, logging in, and the one thing this account type has to be honest
 * about.
 *
 * Email is optional because it was asked to be, and the consequence is stated
 * where the choice is made — not in a help page. An optional-email account whose
 * recovery limits are discovered later is a support burden and a broken promise.
 */
export function AccountPanel({ account, onRegister, onLogin, onLogout, busy }: Props) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [problem, setProblem] = useState<string | null>(null);

  if (account !== null) {
    return (
      <section className="panel account" aria-labelledby="account-heading">
        <h2 id="account-heading">Angemeldet als {account.username}</h2>
        {/* Still true after registration, and the thing people forget. */}
        <p className="hint">{account.recovery_note}</p>
        <button type="button" onClick={() => void onLogout()} disabled={busy}>
          Abmelden
        </button>
      </section>
    );
  }

  const submit = (action: 'register' | 'login') => {
    setProblem(null);
    const name = username.trim();
    if (name === '') {
      setProblem('Bitte einen Benutzernamen angeben.');
      return;
    }
    // Both rules the server enforces, said here rather than arriving as a 422
    // after the form has been filled in.
    if (action === 'register' && name.length < MIN_USERNAME) {
      setProblem(`Der Benutzername braucht mindestens ${MIN_USERNAME} Zeichen.`);
      return;
    }
    if (action === 'register' && !USERNAME_PATTERN.test(name)) {
      setProblem(
        'Im Benutzernamen sind nur Buchstaben, Ziffern, Punkt, Unterstrich und ' +
          'Bindestrich erlaubt.',
      );
      return;
    }
    if (action === 'register' && password.length < MIN_PASSWORD) {
      setProblem(`Das Passwort braucht mindestens ${MIN_PASSWORD} Zeichen.`);
      return;
    }
    if (action === 'login') {
      void onLogin({ username: name, password });
      return;
    }
    const trimmed = email.trim();
    void onRegister({
      username: name,
      password,
      // Absent rather than empty: an empty string is a value, and this field is
      // meant to be genuinely optional.
      ...(trimmed === '' ? {} : { email: trimmed }),
    });
  };

  return (
    <section className="panel account" aria-labelledby="account-heading">
      <h2 id="account-heading">Konto</h2>
      <p className="hint">
        Ein Konto sammelt deine Gärten an einer Stelle. Die Links funktionieren
        weiterhin — das Konto ersetzt sie nicht, es verwahrt sie.
      </p>

      <label htmlFor="account-username">Benutzername</label>
      <input
        id="account-username"
        type="text"
        autoComplete="username"
        value={username}
        disabled={busy}
        aria-describedby="username-rule"
        onChange={(e) => setUsername(e.target.value)}
      />
      {/* The rules the server enforces, where the field is — not as a 422 after
          the form has been filled in. */}
      <p className="hint" id="username-rule">{USERNAME_RULE}</p>

      <label htmlFor="account-password">Passwort</label>
      <input
        id="account-password"
        type="password"
        autoComplete="current-password"
        value={password}
        disabled={busy}
        aria-describedby="password-rule"
        onChange={(e) => setPassword(e.target.value)}
      />
      {/* A hint, not a rule. Nothing here is enforced beyond the length: making
          somebody add a symbol produces "Passwort1!" and not much else. */}
      <p className="hint" id="password-rule">{PASSWORD_HINT}</p>

      <label htmlFor="account-email">E-Mail (optional)</label>
      <input
        id="account-email"
        type="email"
        autoComplete="email"
        value={email}
        disabled={busy}
        onChange={(e) => setEmail(e.target.value)}
      />
      <p className="hint account__warning">{NO_EMAIL_WARNING}</p>

      <div className="account__actions">
        <button type="button" onClick={() => submit('register')} disabled={busy}>
          Konto anlegen
        </button>
        <button type="button" className="link-button" onClick={() => submit('login')} disabled={busy}>
          Anmelden
        </button>
      </div>

      {problem !== null && (
        <p className="hint" role="alert">
          {problem}
        </p>
      )}
    </section>
  );
}
