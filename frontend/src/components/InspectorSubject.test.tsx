import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { InspectorSubject } from './InspectorSubject';

/*
 * The way back is the main route back to the garden (owner's check,
 * 2026-09-21): a filled button before the heading, not a grey link under it.
 */

function subject(onBack = vi.fn()) {
  render(
    <InspectorSubject title="Südbeet" detail="Blumenbeet, 6,0 m²"
                      back={{ label: 'Zurück zum Garten', onBack }} />,
  );
  return onBack;
}

describe('the way back', () => {
  it('comes before the heading, as a button of its own rather than a link', () => {
    subject();
    const back = screen.getByRole('button', { name: 'Zurück zum Garten' });
    const heading = screen.getByRole('heading', { name: 'Südbeet' });
    expect(back.compareDocumentPosition(heading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(back.classList.contains('link-button')).toBe(false);
    expect(back.classList.contains('inspector__back')).toBe(true);
  });

  it('stands outside the subject, so it can stay in sight while the view scrolls', () => {
    // A sticky box sticks only within its parent: inside the subject it would
    // have scrolled away with the title.
    subject();
    const back = screen.getByRole('button', { name: 'Zurück zum Garten' });
    expect(back.closest('.inspector__subject')).toBeNull();
  });

  it('draws its arrow for the eye alone, so its name stays its words', () => {
    subject();
    const back = screen.getByRole('button', { name: 'Zurück zum Garten' });
    const arrow = back.querySelector('[aria-hidden="true"]');
    expect(arrow?.textContent).toBe('←');
  });

  it('goes back when pressed', () => {
    const onBack = subject();
    fireEvent.click(screen.getByRole('button', { name: 'Zurück zum Garten' }));
    expect(onBack).toHaveBeenCalledOnce();
  });
});
