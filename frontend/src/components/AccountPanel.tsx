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

/** Mirrors the server's minimum. Told here rather than after a 422. */
const MIN_PASSWORD = 10;

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
    if (username.trim() === '') {
      setProblem('Bitte einen Benutzernamen angeben.');
      return;
    }
    if (action === 'register' && password.length < MIN_PASSWORD) {
      setProblem(`Das Passwort braucht mindestens ${MIN_PASSWORD} Zeichen.`);
      return;
    }
    if (action === 'login') {
      void onLogin({ username: username.trim(), password });
      return;
    }
    const trimmed = email.trim();
    void onRegister({
      username: username.trim(),
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
        onChange={(e) => setUsername(e.target.value)}
      />

      <label htmlFor="account-password">Passwort</label>
      <input
        id="account-password"
        type="password"
        autoComplete="current-password"
        value={password}
        disabled={busy}
        onChange={(e) => setPassword(e.target.value)}
      />

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
