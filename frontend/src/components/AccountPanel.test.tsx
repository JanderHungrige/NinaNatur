import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { AccountPanel } from './AccountPanel';

function show(props: Partial<Parameters<typeof AccountPanel>[0]> = {}) {
  const onRegister = vi.fn(async () => undefined);
  const onLogin = vi.fn(async () => undefined);
  const onLogout = vi.fn(async () => undefined);
  render(
    <AccountPanel
      account={null}
      onRegister={onRegister}
      onLogin={onLogin}
      onLogout={onLogout}
      busy={false}
      {...props}
    />,
  );
  return { onRegister, onLogin, onLogout };
}

describe('AccountPanel', () => {
  it('says what leaving the email out costs, before it is left out', () => {
    // A limit discovered later is a support burden and a broken promise. The
    // warning is the feature.
    show();
    expect(screen.getByText(/nicht zurückgesetzt werden/)).toBeDefined();
  });

  it('registers without an email', async () => {
    const { onRegister } = show();
    fireEvent.change(screen.getByLabelText(/Benutzername/), { target: { value: 'anna' } });
    fireEvent.change(screen.getByLabelText(/^Passwort/), { target: { value: 'ein langes Passwort' } });
    fireEvent.click(screen.getByRole('button', { name: 'Konto anlegen' }));
    await waitFor(() =>
      expect(onRegister).toHaveBeenCalledWith({
        username: 'anna',
        password: 'ein langes Passwort',
      }),
    );
  });

  it('sends the email only when one was given', async () => {
    const { onRegister } = show();
    fireEvent.change(screen.getByLabelText(/Benutzername/), { target: { value: 'anna' } });
    fireEvent.change(screen.getByLabelText(/^Passwort/), { target: { value: 'ein langes Passwort' } });
    fireEvent.change(screen.getByLabelText(/E-Mail/), { target: { value: 'a@b.de' } });
    fireEvent.click(screen.getByRole('button', { name: 'Konto anlegen' }));
    await waitFor(() => expect(onRegister).toHaveBeenCalled());
    expect(onRegister).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'a@b.de' }),
    );
  });

  it('refuses a password shorter than the server would accept', () => {
    // Told here rather than after a round trip that returns a 422.
    const { onRegister } = show();
    fireEvent.change(screen.getByLabelText(/Benutzername/), { target: { value: 'anna' } });
    fireEvent.change(screen.getByLabelText(/^Passwort/), { target: { value: 'kurz' } });
    fireEvent.click(screen.getByRole('button', { name: 'Konto anlegen' }));
    expect(onRegister).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toBeDefined();
  });

  it('shows who is logged in', () => {
    show({ account: { username: 'anna', email: null, recovery_note: 'kein Reset' } });
    expect(screen.getByText(/anna/)).toBeDefined();
  });

  it('repeats the recovery situation while logged in', () => {
    // It stays true after registration, and it is the thing people forget.
    show({ account: { username: 'anna', email: null, recovery_note: 'kein Reset möglich' } });
    expect(screen.getByText(/kein Reset möglich/)).toBeDefined();
  });

  it('logs out', () => {
    const { onLogout } = show({
      account: { username: 'anna', email: null, recovery_note: 'x' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Abmelden' }));
    expect(onLogout).toHaveBeenCalled();
  });

  it('never puts the password in the DOM as a readable value', () => {
    show();
    const field = screen.getByLabelText(/^Passwort/) as HTMLInputElement;
    expect(field.type).toBe('password');
  });
});

describe('AccountPanel — the rules, where the field is', () => {
  function form() {
    const onRegister = vi.fn(async () => {});
    render(
      <AccountPanel
        account={null}
        onRegister={onRegister}
        onLogin={vi.fn(async () => {})}
        onLogout={vi.fn(async () => {})}
        busy={false}
      />,
    );
    return onRegister;
  }

  it('states the username rule at the username field', () => {
    // It was only enforced on the server, so the first anybody heard of it was
    // a 422 after the whole form had been filled in.
    form();
    const field = screen.getByLabelText('Benutzername');
    const rule = document.getElementById(field.getAttribute('aria-describedby') ?? '');
    expect(rule?.textContent).toMatch(/3 Zeichen/);
    expect(rule?.textContent).toMatch(/Bindestrich/);
  });

  it('refuses a two-letter username before asking the server', () => {
    const onRegister = form();
    fireEvent.change(screen.getByLabelText('Benutzername'), { target: { value: 'jw' } });
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'genug lang' } });
    fireEvent.click(screen.getByRole('button', { name: 'Konto anlegen' }));
    expect(onRegister).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toMatch(/mindestens 3/);
  });

  it('says which characters a username may hold', () => {
    const onRegister = form();
    fireEvent.change(screen.getByLabelText('Benutzername'), { target: { value: 'jan werth' } });
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'genug lang' } });
    fireEvent.click(screen.getByRole('button', { name: 'Konto anlegen' }));
    expect(onRegister).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toMatch(/nur Buchstaben/);
  });

  it('takes an eight-character password', () => {
    // Ten was arbitrary and read as officious. Eight is the floor NIST sets.
    const onRegister = form();
    fireEvent.change(screen.getByLabelText('Benutzername'), { target: { value: 'nina' } });
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'garten12' } });
    fireEvent.click(screen.getByRole('button', { name: 'Konto anlegen' }));
    expect(onRegister).toHaveBeenCalled();
  });

  it('hints at what makes a password stronger without demanding it', () => {
    // A rule that forces a symbol produces "Passwort1!" and not much else.
    const onRegister = form();
    const rule = document.getElementById(
      screen.getByLabelText('Passwort').getAttribute('aria-describedby') ?? '',
    );
    expect(rule?.textContent).toMatch(/Sonderzeichen/);
    fireEvent.change(screen.getByLabelText('Benutzername'), { target: { value: 'nina' } });
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'nurbuchstaben' } });
    fireEvent.click(screen.getByRole('button', { name: 'Konto anlegen' }));
    expect(onRegister).toHaveBeenCalled();
  });
});
