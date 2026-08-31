import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { MyGardens } from './MyGardens';

const GARDENS = [
  { name: 'Südbeet', share_token: 'tok-a', updated_at: new Date().toISOString() },
  {
    name: 'Schrebergarten',
    share_token: 'tok-b',
    updated_at: new Date(Date.now() - 3 * 86_400_000).toISOString(),
  },
];

function list(props: Partial<Parameters<typeof MyGardens>[0]> = {}) {
  const onOpen = vi.fn();
  const onDelete = vi.fn();
  render(
    <MyGardens gardens={GARDENS} onOpen={onOpen} onDelete={onDelete} busy={false} {...props} />,
  );
  return { onOpen, onDelete };
}

describe('MyGardens', () => {
  it('lists what the account has claimed', () => {
    list();
    expect(screen.getByText('Südbeet')).toBeDefined();
    expect(screen.getByText('Schrebergarten')).toBeDefined();
  });

  it('opens one by its token', () => {
    const { onOpen } = list();
    fireEvent.click(screen.getByText('Südbeet'));
    expect(onOpen).toHaveBeenCalledWith('tok-a');
  });

  it('says when each was last touched, in words', () => {
    list();
    expect(screen.getByText(/heute geändert/)).toBeDefined();
    expect(screen.getByText(/vor 3 Tagen/)).toBeDefined();
  });

  it('asks before deleting', () => {
    // A garden cannot be got back. One click away from gone is one too few.
    const { onDelete } = list();
    fireEvent.click(screen.getByRole('button', { name: 'Südbeet löschen' }));
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Endgültig löschen' })).toBeDefined();
  });

  it('deletes once, and only the one that was asked about', () => {
    const { onDelete } = list();
    fireEvent.click(screen.getByRole('button', { name: 'Schrebergarten löschen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Endgültig löschen' }));
    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(onDelete).toHaveBeenCalledWith('tok-b');
  });

  it('lets the question be withdrawn', () => {
    const { onDelete } = list();
    fireEvent.click(screen.getByRole('button', { name: 'Südbeet löschen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(onDelete).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Südbeet löschen' })).toBeDefined();
  });

  it('asks about one garden at a time', () => {
    // Two open confirmations is two chances to hit the wrong one.
    list();
    fireEvent.click(screen.getByRole('button', { name: 'Südbeet löschen' }));
    fireEvent.click(screen.getByRole('button', { name: 'Schrebergarten löschen' }));
    expect(screen.getAllByRole('button', { name: 'Endgültig löschen' })).toHaveLength(1);
  });

  it('says so when there are none yet', () => {
    list({ gardens: [] });
    expect(screen.getByText(/Noch keiner/)).toBeDefined();
  });
});
