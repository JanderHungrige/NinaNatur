import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { AccountBar } from './AccountBar';

function bar(props: Partial<Parameters<typeof AccountBar>[0]> = {}) {
  const onSignIn = vi.fn();
  const onSignUp = vi.fn();
  const onSignOut = vi.fn();
  render(
    <AccountBar
      username={null}
      onSignIn={onSignIn}
      onSignUp={onSignUp}
      onSignOut={onSignOut}
      inviting
      busy={false}
      {...props}
    />,
  );
  return { onSignIn, onSignUp, onSignOut };
}

describe('AccountBar', () => {
  it('offers both ways in', () => {
    const { onSignIn, onSignUp } = bar();
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }));
    fireEvent.click(screen.getByRole('button', { name: 'Konto anlegen' }));
    expect(onSignIn).toHaveBeenCalled();
    expect(onSignUp).toHaveBeenCalled();
  });

  it('says an account is optional, and why it is still worth it', () => {
    bar();
    const note = screen.getByText(/nicht nötig/);
    expect(note.textContent).toMatch(/Link verlierst/);
  });

  it('ties the note to the button it is about', () => {
    // A sentence floating beside a button is not connected to it for anyone
    // who cannot see the arrow.
    bar();
    const signup = screen.getByRole('button', { name: 'Konto anlegen' });
    expect(signup.getAttribute('aria-describedby')).toBe('signup-note');
  });

  it('hides the arrow from anything that reads the page', () => {
    // It is decoration; the sentence carries the meaning.
    const { container } = render(
      <AccountBar
        username={null} onSignIn={vi.fn()} onSignUp={vi.fn()} onSignOut={vi.fn()}
        inviting busy={false}
      />,
    );
    expect(container.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true');
  });

  it('drops the invitation once somebody is signed in', () => {
    bar({ username: 'nina' });
    expect(screen.queryByText(/nicht nötig/)).toBeNull();
    expect(screen.getByText(/Angemeldet als nina/)).toBeDefined();
  });

  it('shows no invitation away from the front door', () => {
    // Inside a garden the bar is just a way out, not a pitch.
    bar({ inviting: false });
    expect(screen.queryByText(/nicht nötig/)).toBeNull();
    expect(screen.getByRole('button', { name: 'Konto anlegen' })).toBeDefined();
  });

  it('signs out', () => {
    const { onSignOut } = bar({ username: 'nina' });
    fireEvent.click(screen.getByRole('button', { name: 'Abmelden' }));
    expect(onSignOut).toHaveBeenCalled();
  });
});
