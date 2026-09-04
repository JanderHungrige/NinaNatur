import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ElementMenu } from './ElementMenu';

function open(props: Partial<Parameters<typeof ElementMenu>[0]> = {}) {
  const onSave = vi.fn();
  const onClose = vi.fn();
  render(
    <ElementMenu
      elementId={7}
      at={{ x: 120, y: 80 }}
      kind="other"
      label={null}
      area={24}
      plantings={0}
      shape="polygon" height={null} width={null} soilType={null} moisture={null} heightAboveGround={0}
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
  it('anchors to the shape, not to the pointer', () => {
    // Wave 15. It used to sit at the click coordinate and stay there: a shape
    // low in the window put half the menu below the fold, and because the menu
    // is `position: fixed`, scrolling moved the page and the shape but never
    // the menu. Anchoring is what lets it follow.
    const shape = document.createElement('div');
    shape.setAttribute('data-element-id', '7');
    shape.getBoundingClientRect = () =>
      ({ left: 300, top: 200, right: 400, bottom: 260, width: 100, height: 60,
         x: 300, y: 200, toJSON: () => ({}) }) as DOMRect;
    document.body.append(shape);

    open();

    const menu = screen.getByRole('dialog', { name: 'Was ist das?' });
    expect(menu.style.left).toBe('300px');
    expect(menu.style.top).toBe('266px');
    shape.remove();
  });

  it('falls back to the pointer when the shape has gone', () => {
    // Deleting an element while its menu is open, or a plan that has re-drawn
    // since. Not off-screen, not at the origin: near where the hand was.
    open();
    const menu = screen.getByRole('dialog', { name: 'Was ist das?' });
    expect(menu.style.left).toBe('120px');
    expect(Number.parseInt(menu.style.top, 10)).toBeGreaterThanOrEqual(80);
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
        elementId={7}
        at={{ x: 0, y: 0 }} kind="pond" label="Der alte Teich" area={12.5}
        plantings={0} shape="polygon" height={null} width={null} soilType={null} moisture={null} heightAboveGround={0}
        onSave={vi.fn()} onDelete={vi.fn()} onClose={vi.fn()} busy={false}
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
          elementId={7}
          at={{ x: 0, y: 0 }} kind="pond" label={null} area={4}
          plantings={0} shape="polygon" height={null} width={null} soilType={null} moisture={null} heightAboveGround={0}
        onSave={vi.fn()} onDelete={vi.fn()} onClose={onClose} busy={false}
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
        elementId={7}
        at={{ x: 0, y: 0 }} kind="pond" label={null} area={4}
        plantings={0} shape="polygon" height={null} width={null} soilType={null} moisture={null} heightAboveGround={0}
        onSave={vi.fn()} onDelete={vi.fn()} onClose={onClose} busy={false}
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
          elementId={7}
          at={{ x: 0, y: 0 }} kind="pond" label={null} area={4}
          plantings={0} shape="polygon" height={null} width={null} soilType={null} moisture={null} heightAboveGround={0}
        onSave={vi.fn()} onDelete={vi.fn()} onClose={onClose} busy={false}
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
        elementId={7}
        at={{ x: 0, y: 0 }} kind="pond" label={null} area={12} plantings={0} shape="polygon" height={null} width={null} soilType={null} moisture={null} heightAboveGround={0}
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
