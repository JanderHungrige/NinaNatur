import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { type StatusMessage, StatusToast, readingTime } from './StatusToast';

function said(text: string, stamp: number, tone: StatusMessage['tone'] = 'info'): StatusMessage {
  return { text, tone, stamp };
}

/** The toast around the live region: its class is the only thing jsdom can see of "shown". */
function toast(): HTMLElement {
  const outer = screen.getByRole('status').closest('.status-toast');
  if (!(outer instanceof HTMLElement)) throw new Error('the live region is not inside the toast');
  return outer;
}

const shown = (): boolean => toast().classList.contains('status-toast--shown');

describe('StatusToast', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('keeps a polite live region in the page before anything has been said', () => {
    // A region that appears together with its first message is often not
    // announced at all: it has to be there first.
    render(<StatusToast message={said('', 0)} />);
    const region = screen.getByRole('status');
    expect(region.getAttribute('aria-live')).toBe('polite');
    expect(region.textContent).toBe('');
    expect(shown()).toBe(false);
  });

  it('shows what was said, and says it in the live region', () => {
    render(<StatusToast message={said('Beet Südbeet hinzugefügt.', 1)} />);
    expect(screen.getByRole('status').textContent).toBe('Beet Südbeet hinzugefügt.');
    expect(shown()).toBe(true);
  });

  it('lets a message that needs nothing go once it could have been read', () => {
    const text = 'Beet Südbeet hinzugefügt.';
    render(<StatusToast message={said(text, 1)} />);
    act(() => {
      vi.advanceTimersByTime(readingTime(text) - 1);
    });
    expect(shown()).toBe(true);
    act(() => {
      vi.advanceTimersByTime(2);
    });
    expect(shown()).toBe(false);
    expect(screen.getByRole('status').textContent).toBe('');
  });

  it('keeps a failure until it is closed, and the button is not read as part of it', () => {
    render(<StatusToast message={said('Speichern fehlgeschlagen: Netzwerkfehler', 2, 'problem')} />);
    act(() => {
      vi.advanceTimersByTime(60_000);
    });
    expect(shown()).toBe(true);
    const close = screen.getByRole('button', { name: 'Schließen' });
    expect(screen.getByRole('status').contains(close)).toBe(false);
    fireEvent.click(close);
    expect(shown()).toBe(false);
  });

  it('shows the same words again when they are said again', () => {
    const { rerender } = render(<StatusToast message={said('Achillea millefolium gepflanzt.', 1)} />);
    act(() => {
      vi.advanceTimersByTime(20_000);
    });
    expect(shown()).toBe(false);
    rerender(<StatusToast message={said('Achillea millefolium gepflanzt.', 2)} />);
    expect(shown()).toBe(true);
    expect(screen.getByRole('status').textContent).toBe('Achillea millefolium gepflanzt.');
  });

  it('gives a long message longer than a short one, between 5 and 15 seconds', () => {
    expect(readingTime('Angemeldet.')).toBe(5000);
    expect(readingTime('x'.repeat(120))).toBeGreaterThan(readingTime('Angemeldet.'));
    expect(readingTime('x'.repeat(1000))).toBe(15000);
  });
});
