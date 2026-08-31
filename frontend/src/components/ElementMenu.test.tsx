import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ElementMenu } from './ElementMenu';

function open(props: Partial<Parameters<typeof ElementMenu>[0]> = {}) {
  const onSave = vi.fn();
  const onClose = vi.fn();
  render(
    <ElementMenu
      at={{ x: 120, y: 80 }}
      kind="other"
      label={null}
      area={24}
      onSave={onSave}
      onClose={onClose}
      busy={false}
      {...props}
    />,
  );
  return { onSave, onClose };
}

describe('ElementMenu', () => {
  it('opens where the pointer was', () => {
    open();
    const menu = screen.getByRole('dialog', { name: 'Was ist das?' });
    expect(menu.style.left).toBe('120px');
    expect(menu.style.top).toBe('80px');
  });

  it('saves the kind and the label together', () => {
    const { onSave } = open();
    fireEvent.change(screen.getByLabelText('Art'), { target: { value: 'pond' } });
    fireEvent.change(screen.getByLabelText('Bezeichnung'), {
      target: { value: 'Der alte Teich' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Übernehmen' }));
    expect(onSave).toHaveBeenCalledWith({ kind: 'pond', label: 'Der alte Teich' });
  });

  it('takes the focus when it opens', () => {
    // A menu that opens away from the keyboard is a menu the keyboard cannot
    // reach.
    open();
    expect(document.activeElement).toBe(screen.getByLabelText('Art'));
  });

  it('closes on Escape', () => {
    const { onClose } = open();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('starts from what the element already is', () => {
    open({ kind: 'hedge', label: 'Nachbars Hecke' });
    expect((screen.getByLabelText('Art') as HTMLSelectElement).value).toBe('hedge');
    expect((screen.getByLabelText('Bezeichnung') as HTMLInputElement).value).toBe(
      'Nachbars Hecke',
    );
  });
});

describe('ElementMenu — which element is this?', () => {
  it('names what it is about, so an overlap does not fool the user', () => {
    // Two shapes on top of each other take the same right-click. Without this
    // the user names one and watches the other not change — which reads as the
    // menu not saving at all.
    render(
      <ElementMenu
        at={{ x: 0, y: 0 }} kind="pond" label="Der alte Teich" area={12.5}
        onSave={vi.fn()} onClose={vi.fn()} busy={false}
      />,
    );
    const subject = screen.getByRole('dialog').textContent ?? '';
    expect(subject).toMatch(/Teich/);
    expect(subject).toMatch(/12,5 m²/);
  });
});

describe('ElementMenu — getting out of the way', () => {
  it('closes when something else is clicked', () => {
    // Clicking another shape while the menu is open left it hanging over the
    // plan, still asking about the shape before.
    const onClose = vi.fn();
    render(
      <>
        <button type="button">anderes Objekt</button>
        <ElementMenu
          at={{ x: 0, y: 0 }} kind="pond" label={null} area={4}
          onSave={vi.fn()} onClose={onClose} busy={false}
        />
      </>,
    );
    fireEvent.pointerDown(screen.getByRole('button', { name: 'anderes Objekt' }));
    expect(onClose).toHaveBeenCalled();
  });

  it('stays open while it is being used', () => {
    // Closing on any pointerdown would close it the moment somebody reached
    // for its own select.
    const onClose = vi.fn();
    render(
      <ElementMenu
        at={{ x: 0, y: 0 }} kind="pond" label={null} area={4}
        onSave={vi.fn()} onClose={onClose} busy={false}
      />,
    );
    fireEvent.pointerDown(screen.getByLabelText('Art'));
    expect(onClose).not.toHaveBeenCalled();
  });
});

describe('ElementMenu — a click that stops propagating', () => {
  it('still closes when the click is swallowed on its way up', () => {
    // Grabbing a shape calls stopPropagation so the plan does not read it as a
    // pan. A bubbling listener would never hear the click on another shape —
    // which is precisely the one this needs to hear.
    const onClose = vi.fn();
    render(
      <>
        <button
          type="button"
          onPointerDown={(event) => event.stopPropagation()}
        >
          anderes Objekt
        </button>
        <ElementMenu
          at={{ x: 0, y: 0 }} kind="pond" label={null} area={4}
          onSave={vi.fn()} onClose={onClose} busy={false}
        />
      </>,
    );
    fireEvent.pointerDown(screen.getByRole('button', { name: 'anderes Objekt' }));
    expect(onClose).toHaveBeenCalled();
  });
});
