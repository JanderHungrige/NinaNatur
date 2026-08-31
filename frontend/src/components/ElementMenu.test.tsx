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
