import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { GardenOut, NinaNaturClient, ShadowMark } from '../api/client';
import { garden } from '../testing/gardens';
import type { Status } from '../useStatus';
import { useShadowMarks } from './useShadowMarks';

/* Marking a shadow edge from an element's details (doc 122): the next click on
   the plan places it, at the moment of that click unless another is typed;
   readings are re-read with the garden, and only the newest answer counts. */

function seen(markId: number): ShadowMark {
  return { mark_id: markId, element_id: 7, x: 1, y: 2, seen_at: '2026-06-21T09:30:00+00:00',
           reading: null };
}

/** A promise that answers when the test says so. */
function later<T>() {
  let answer: (value: T) => void = () => undefined;
  const promise = new Promise<T>((resolve) => {
    answer = resolve;
  });
  return { promise, answer };
}

type FakeClient = {
  shadowMarks: ReturnType<typeof vi.fn<() => Promise<ShadowMark[]>>>;
  markShadow: ReturnType<typeof vi.fn>;
  forgetShadowMark: ReturnType<typeof vi.fn>;
};

function setup(existing: ShadowMark[] = [], prepare: (client: FakeClient) => void = () => {}) {
  // Keeps what it is given, as the server does: a re-read returns the new mark.
  let stored = [...existing];
  const client = {
    shadowMarks: vi.fn(async (): Promise<ShadowMark[]> => stored),
    markShadow: vi.fn(async () => {
      stored = [...stored, seen(99)];
      return seen(99);
    }),
    forgetShadowMark: vi.fn(async (_token: string, markId: number) => {
      stored = stored.filter((mark) => mark.mark_id !== markId);
    }),
  };
  const setStatus = vi.fn();
  const status = {
    run: vi.fn(async (_label: string, action: () => Promise<void>) => action()),
    setStatus,
  } as unknown as Status;
  const setTool = vi.fn();
  prepare(client as unknown as FakeClient);
  const hook = renderHook(
    ({ plan }: { plan: GardenOut }) =>
      useShadowMarks(client as unknown as NinaNaturClient, plan, status, setTool),
    { initialProps: { plan: garden('tok', 'G') } },
  );
  return { ...hook, client, setTool, setStatus };
}

afterEach(() => {
  vi.useRealTimers();
});

describe('useShadowMarks', () => {
  it('reads the garden\'s marks when it opens', async () => {
    const { result, client } = setup([seen(1)]);
    await waitFor(() => expect(result.current.marks).toHaveLength(1));
    expect(client.shadowMarks).toHaveBeenCalledWith('tok');
  });

  it('places at the moment of the click, not when the garden was opened', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-06-21T07:00:00Z'));
    const { result, client, setTool } = setup();
    await waitFor(() => expect(client.shadowMarks).toHaveBeenCalled());
    act(() => result.current.arm(7));
    expect(setTool).toHaveBeenCalledWith('shadowmark');
    expect(result.current.target).toBe(7);

    vi.setSystemTime(new Date('2026-06-21T11:00:00Z'));
    await act(async () => result.current.place(1.25, -3.5));

    expect(client.markShadow).toHaveBeenCalledWith('tok', {
      element_id: 7, x: 1.25, y: -3.5, seen_at: '2026-06-21T11:00:00.000Z',
    });
    expect(result.current.marks.map((m) => m.mark_id)).toEqual([99]);
  });

  it('places at a typed moment, and at now again once the field is emptied', async () => {
    const { result, client } = setup();
    await waitFor(() => expect(client.shadowMarks).toHaveBeenCalled());
    act(() => result.current.setSeenAt('2026-06-21T11:30'));
    act(() => result.current.arm(7));
    await act(async () => result.current.place(1, 1));
    expect(client.markShadow).toHaveBeenLastCalledWith('tok', expect.objectContaining({
      seen_at: '2026-06-21T09:30:00.000Z' }));

    act(() => result.current.setSeenAt(''));
    expect(result.current.seenAt).toBeNull();
  });

  it('says what the placed mark found', async () => {
    const { result, client, setStatus } = setup();
    await waitFor(() => expect(client.shadowMarks).toHaveBeenCalled());
    act(() => result.current.arm(7));
    await act(async () => result.current.place(1, 1));
    expect(setStatus).toHaveBeenLastCalledWith(
      'Dieses Element wirft zu diesem Zeitpunkt keinen Schatten mehr.');
  });

  it('places nothing unless an element armed it, and puts an armed one down', async () => {
    const { result, client, setTool } = setup();
    await act(async () => result.current.place(1, 1));
    expect(client.markShadow).not.toHaveBeenCalled();
    act(() => result.current.arm(7));
    act(() => result.current.disarm());
    expect(result.current.target).toBeNull();
    expect(setTool).toHaveBeenLastCalledWith(null);
  });

  it('forgets a mark', async () => {
    const { result, client } = setup([seen(1), seen(2)]);
    await waitFor(() => expect(result.current.marks).toHaveLength(2));
    await act(async () => result.current.remove(1));
    expect(client.forgetShadowMark).toHaveBeenCalledWith('tok', 1);
    expect(result.current.marks.map((m) => m.mark_id)).toEqual([2]);
  });

  it('keeps the first answer, though the garden changed while it was asked', async () => {
    // Dropping that answer left the marks hidden for the whole visit (review).
    const first = later<ShadowMark[]>();
    const { result, client, rerender } = setup([seen(4)], (fake) => {
      fake.shadowMarks.mockImplementationOnce(() => first.promise);
    });
    rerender({ plan: garden('tok', 'G, geändert') });
    expect(client.shadowMarks).toHaveBeenCalledTimes(1);
    await act(async () => first.answer([seen(4)]));
    expect(result.current.marks.map((m) => m.mark_id)).toEqual([4]);
  });

  it('lets no older answer overwrite a mark placed since', async () => {
    const { result, client, rerender } = setup([seen(1)]);
    await waitFor(() => expect(result.current.marks).toHaveLength(1));
    const stale = later<ShadowMark[]>();
    client.shadowMarks.mockImplementationOnce(() => stale.promise);
    rerender({ plan: garden('tok', 'G, geändert') });
    act(() => result.current.arm(7));
    await act(async () => result.current.place(1, 1));
    await act(async () => stale.answer([seen(1)]));
    expect(result.current.marks.map((m) => m.mark_id)).toEqual([1, 99]);
  });

  it('says so when the marks cannot be read', async () => {
    const { setStatus } = setup([], (fake) => {
      fake.shadowMarks.mockRejectedValueOnce(new Error('offline'));
    });
    await waitFor(() => expect(setStatus).toHaveBeenCalledWith(
      'Schattenmarkierungen konnten nicht gelesen werden.', 'problem'));
  });

  it('re-reads with every change of a garden that has marks, and not one without', async () => {
    const without = setup();
    await waitFor(() => expect(without.client.shadowMarks).toHaveBeenCalledTimes(1));
    without.rerender({ plan: garden('tok', 'G, geändert') });
    without.rerender({ plan: garden('tok', 'G, noch einmal') });
    expect(without.client.shadowMarks).toHaveBeenCalledTimes(1);

    const marked = setup([seen(1)]);
    await waitFor(() => expect(marked.result.current.marks).toHaveLength(1));
    const before = marked.client.shadowMarks.mock.calls.length;
    marked.rerender({ plan: garden('tok', 'G, geändert') });
    await waitFor(() => expect(marked.client.shadowMarks.mock.calls.length).toBe(before + 1));
  });
});
