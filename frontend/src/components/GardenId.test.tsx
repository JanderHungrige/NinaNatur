import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { GardenId } from './GardenId';

afterEach(() => vi.unstubAllGlobals());

function show(copy?: (text: string) => Promise<void>) {
  if (copy !== undefined) {
    vi.stubGlobal('navigator', { clipboard: { writeText: copy } });
  }
  render(<GardenId token="abc123" />);
}

describe('GardenId', () => {
  it('shows the id, because it is the only way back', () => {
    show();
    expect(screen.getByText('abc123')).toBeDefined();
  });

  it('says what the id is for', () => {
    show();
    expect(screen.getByText(/kommst du wieder/i)).toBeDefined();
  });

  it('says what sharing it means', () => {
    // It is a credential, not a row number. Anyone holding it can edit and
    // delete the garden, and the wording must not read as harmless.
    show();
    expect(screen.getByText(/ändern/i)).toBeDefined();
  });

  it('copies it', async () => {
    const copy = vi.fn(async () => undefined);
    show(copy);
    fireEvent.click(screen.getByRole('button', { name: /kopieren/i }));
    await waitFor(() => expect(copy).toHaveBeenCalledWith('abc123'));
  });

  it('confirms the copy happened', async () => {
    show(vi.fn(async () => undefined));
    fireEvent.click(screen.getByRole('button', { name: /kopieren/i }));
    await waitFor(() => expect(screen.getByText(/kopiert/i)).toBeDefined());
  });

  it('says so when copying fails instead of doing nothing visible', async () => {
    // navigator.clipboard needs a secure context and a permission. A button
    // that silently does nothing is worse than one that admits it.
    show(vi.fn(async () => { throw new Error('denied'); }));
    fireEvent.click(screen.getByRole('button', { name: /kopieren/i }));
    await waitFor(() => expect(screen.getByText(/nicht kopieren/i)).toBeDefined());
  });

  it('leaves the id selectable when copying is unavailable', () => {
    vi.stubGlobal('navigator', {});
    render(<GardenId token="abc123" />);
    expect(screen.getByText('abc123')).toBeDefined();
  });
});
