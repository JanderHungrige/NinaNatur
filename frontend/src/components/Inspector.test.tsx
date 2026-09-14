import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Inspector } from './Inspector';

describe('Inspector', () => {
  it('is the complementary region named Details, and holds what it is given', () => {
    render(
      <Inspector wide={false} onWide={vi.fn()}>
        <p>Beete</p>
      </Inspector>,
    );
    expect(screen.getByRole('complementary', { name: 'Details' }).textContent).toContain('Beete');
  });

  it('offers the wide view as a toggle that keeps its name and says its state', () => {
    // One name in both states: a label that flips *and* a pressed state tell a
    // screen reader the same thing twice, and one of them wrongly.
    const onWide = vi.fn();
    render(
      <Inspector wide={false} onWide={onWide}>
        <p />
      </Inspector>,
    );
    const toggle = screen.getByRole('button', { name: 'Breite Ansicht' });
    expect(toggle.getAttribute('aria-pressed')).toBe('false');
    fireEvent.click(toggle);
    expect(onWide).toHaveBeenCalledWith(true);
  });

  it('turns the wide view off again', () => {
    const onWide = vi.fn();
    render(
      <Inspector wide onWide={onWide}>
        <p />
      </Inspector>,
    );
    const toggle = screen.getByRole('button', { name: 'Breite Ansicht' });
    expect(toggle.getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(toggle);
    expect(onWide).toHaveBeenCalledWith(false);
  });
});

/* Doc 91: on a narrow window the details are a sheet from below. */

type Snap = 'peek' | 'half' | 'full';

function sheet(snap: Snap, children = <p>Beete</p>) {
  const control = { snap, onSnap: vi.fn(), onDrag: vi.fn() };
  const view = render(
    <Inspector wide={false} onWide={vi.fn()} sheet={control}>
      {children}
    </Inspector>,
  );
  const again = (next: Snap) =>
    view.rerender(
      <Inspector wide={false} onWide={vi.fn()} sheet={{ ...control, snap: next }}>
        {children}
      </Inspector>,
    );
  return { ...control, again, aside: screen.getByRole('complementary', { name: 'Details' }) };
}

function listening() {
  const heard = vi.fn();
  window.addEventListener('keydown', heard);
  return { heard, stop: () => window.removeEventListener('keydown', heard) };
}

function outsideButton() {
  const outside = document.createElement('button');
  outside.textContent = 'Plan';
  document.body.prepend(outside);
  return outside;
}

describe('Inspector as a sheet', () => {
  it('has no handle beside a wide plan', () => {
    render(
      <Inspector wide={false} onWide={vi.fn()}>
        <p />
      </Inspector>,
    );
    expect(screen.queryByRole('separator')).toBeNull();
    expect(screen.getByRole('complementary').hasAttribute('data-snap')).toBe(false);
  });

  it('says its height and puts its handle first, sizing these details', () => {
    const { aside } = sheet('half');
    expect(aside.getAttribute('data-snap')).toBe('half');
    const handle = screen.getByRole('separator', { name: 'Höhe der Details' });
    expect(aside.firstElementChild).toBe(handle);
    expect(handle.getAttribute('aria-controls')).toBe(aside.id);
  });

  it('comes down from 90 % on Escape, and the page’s Escape never hears it', () => {
    // At 90 % Escape leaves the trap; the plan's own Escape would clear the selection (doc 88).
    const { heard, stop } = listening();
    const { onSnap } = sheet('full', <button type="button">Pflanzen</button>);
    fireEvent.keyDown(screen.getByRole('button', { name: 'Pflanzen' }), { key: 'Escape' });
    expect(onSnap).toHaveBeenCalledWith('half');
    expect(heard).not.toHaveBeenCalled();
    stop();
  });

  it('leaves Escape to the page below 90 %', () => {
    const { heard, stop } = listening();
    const { onSnap, aside } = sheet('half');
    fireEvent.keyDown(aside, { key: 'Escape' });
    expect(onSnap).not.toHaveBeenCalled();
    expect(heard).toHaveBeenCalledTimes(1);
    stop();
  });

  it('leaves Escape typed into a text field alone, even at 90 %', () => {
    const { onSnap } = sheet('full', <input aria-label="Pflanze" />);
    fireEvent.keyDown(screen.getByLabelText('Pflanze'), { key: 'Escape' });
    expect(onSnap).not.toHaveBeenCalled();
  });

  it('makes everything outside it inert at 90 %, and gives it back below', () => {
    const outside = outsideButton();
    const { again, aside } = sheet('full');
    expect(outside.hasAttribute('inert')).toBe(true);
    expect(aside.closest('[inert]')).toBeNull();
    again('half');
    expect(outside.hasAttribute('inert')).toBe(false);
    outside.remove();
  });

  it('keeps what was inert before it rose inert after it comes down', () => {
    const outside = outsideButton();
    outside.setAttribute('inert', '');
    const { again } = sheet('full');
    again('peek');
    expect(outside.hasAttribute('inert')).toBe(true);
    outside.remove();
  });

  it('takes the focus in when it rises to 90 % with the focus outside', () => {
    const outside = outsideButton();
    outside.focus();
    const { aside } = sheet('full');
    expect(aside.contains(document.activeElement)).toBe(true);
    outside.remove();
  });
});
