import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useStatus } from './useStatus';

/** A request the test finishes by hand. */
function deferred() {
  let finish: () => void = () => undefined;
  let fail: (error: Error) => void = () => undefined;
  const promise = new Promise<void>((resolve, reject) => {
    finish = resolve;
    fail = reject;
  });
  return { promise, finish, fail };
}

describe('useStatus — what is running', () => {
  it('stays busy until the last of two overlapping requests is done', async () => {
    // As a flag, the first to finish cleared it and every button came back
    // while the second was still on its way.
    const { result } = renderHook(() => useStatus());
    const first = deferred();
    const second = deferred();
    let firstRun: Promise<void> = Promise.resolve();
    let secondRun: Promise<void> = Promise.resolve();

    act(() => {
      firstRun = result.current.run('Speichern', () => first.promise);
      secondRun = result.current.run('Pflanzen', () => second.promise);
    });
    expect(result.current.busy).toBe(true);

    await act(async () => {
      first.finish();
      await firstRun;
    });
    expect(result.current.busy).toBe(true);
    expect(result.current.working).toBe('Pflanzen');

    await act(async () => {
      second.finish();
      await secondRun;
    });
    expect(result.current.busy).toBe(false);
    expect(result.current.working).toBeNull();
  });

  it('names the newest request, and the older one again once the newest is done', async () => {
    const { result } = renderHook(() => useStatus());
    const older = deferred();
    const newer = deferred();
    let newerRun: Promise<void> = Promise.resolve();

    act(() => {
      void result.current.run('Speichern', () => older.promise);
      newerRun = result.current.run('Schatten neu berechnen', () => newer.promise);
    });
    expect(result.current.working).toBe('Schatten neu berechnen');

    await act(async () => {
      newer.finish();
      await newerRun;
    });
    expect(result.current.working).toBe('Speichern');
  });

  it('counts two requests with the same label as two', async () => {
    const { result } = renderHook(() => useStatus());
    const one = deferred();
    const two = deferred();
    let oneRun: Promise<void> = Promise.resolve();

    act(() => {
      oneRun = result.current.run('Verschieben', () => one.promise);
      void result.current.run('Verschieben', () => two.promise);
    });
    await act(async () => {
      one.finish();
      await oneRun;
    });
    expect(result.current.busy).toBe(true);
  });

  it('is idle again after a failure, and says what failed', async () => {
    const { result } = renderHook(() => useStatus());
    const request = deferred();
    let run: Promise<void> = Promise.resolve();

    act(() => {
      run = result.current.run('Speichern', () => request.promise);
    });
    await act(async () => {
      request.fail(new Error('500: kaputt'));
      await run;
    });
    expect(result.current.busy).toBe(false);
    expect(result.current.status.text).toBe('Speichern fehlgeschlagen: 500: kaputt');
    expect(result.current.status.tone).toBe('problem');
  });
});
