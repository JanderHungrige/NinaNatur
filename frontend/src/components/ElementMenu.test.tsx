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
      plantings={0}
      onDelete={vi.fn()}
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
        plantings={0} onSave={vi.fn()} onDelete={vi.fn()} onClose={vi.fn()} busy={false}
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
          plantings={0} onSave={vi.fn()} onDelete={vi.fn()} onClose={onClose} busy={false}
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
        plantings={0} onSave={vi.fn()} onDelete={vi.fn()} onClose={onClose} busy={false}
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
          plantings={0} onSave={vi.fn()} onDelete={vi.fn()} onClose={onClose} busy={false}
        />
      </>,
    );
    fireEvent.pointerDown(screen.getByRole('button', { name: 'anderes Objekt' }));
    expect(onClose).toHaveBeenCalled();
  });
});

describe('ElementMenu — deleting', () => {
  function open(props: Partial<Parameters<typeof ElementMenu>[0]> = {}) {
    const onDelete = vi.fn();
    const onClose = vi.fn();
    render(
      <ElementMenu
        at={{ x: 0, y: 0 }} kind="pond" label={null} area={12} plantings={0}
        onSave={vi.fn()} onDelete={onDelete} onClose={onClose} busy={false}
        {...props}
      />,
    );
    return { onDelete, onClose };
  }

  it('asks before deleting', () => {
    // An element cannot be got back, and this menu is one right-click away
    // from every shape on the plan.
    const { onDelete } = open();
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Endgültig löschen' })).toBeDefined();
  });

  it('deletes once confirmed', () => {
    const { onDelete } = open();
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Endgültig löschen' }));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });

  it('says what a planted bed costs before it goes', () => {
    // The same warning re-labelling gives, for the same reason: the plants go
    // with it and nobody should find that out afterwards.
    open({ kind: 'bed', plantings: 7 });
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    expect(screen.getByRole('alert').textContent).toMatch(/7 Pflanzen/);
  });

  it('says nothing about plants when there are none', () => {
    open({ kind: 'bed', plantings: 0 });
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('lets the question be withdrawn', () => {
    const { onDelete } = open();
    fireEvent.click(screen.getByRole('button', { name: 'Löschen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Doch nicht' }));
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Löschen' })).toBeDefined();
  });
});
