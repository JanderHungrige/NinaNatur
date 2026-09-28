import { useCallback, useEffect, useRef, useState } from 'react';

import type { GardenOut, NinaNaturClient, ShadowMark } from '../api/client';
import type { Tool } from '../canvas/shapes';
import { localToIso, readingWords } from '../shadowMarks';
import type { Status } from '../useStatus';

/**
 * Where the gardener saw shadows end, and marking another (doc 122).
 *
 * A mark is armed from an element's details — whose shadow it is — and placed
 * by the next click on the plan. Its moment is *now*, the moment of that
 * click, unless the gardener typed another: the field used to start at the
 * time the garden was opened, and a mark placed hours later was read against
 * that sun and blamed on the plan (review, 2026-09-28).
 *
 * Each reading is the model's as it is now, so the marks are read again with
 * every change to a garden that has any. Each read is numbered, and only the
 * newest answer, given after the last mark placed or forgotten, is kept:
 * dropping an answer when the garden changed left a garden opened and edited
 * at once without its marks, and an older read could overwrite a new mark.
 */
export function useShadowMarks(
  client: NinaNaturClient,
  garden: GardenOut,
  status: Status,
  setTool: (tool: Tool | null) => void,
) {
  const { run, setStatus } = status;
  const token = garden.share_token;
  const [marks, setMarks] = useState<ShadowMark[]>([]);
  /** The element whose shadow the next click marks. */
  const [target, setTarget] = useState<number | null>(null);
  /** The moment the gardener typed, as a `datetime-local` value; null is now. */
  const [seenAt, setSeen] = useState<string | null>(null);

  const asked = useRef(0);
  const read = useRef(false);
  const hasMarks = marks.length > 0;
  useEffect(() => {
    // A garden without marks is read once; one with marks on every change.
    if (read.current && !hasMarks) return;
    read.current = true;
    const ask = ++asked.current;
    client
      .shadowMarks(token)
      .then((found) => {
        if (ask === asked.current) setMarks(found);
      })
      .catch(() => {
        if (ask !== asked.current) return;
        read.current = false;
        // Said, never swallowed: marks the page cannot read are not "none".
        setStatus('Schattenmarkierungen konnten nicht gelesen werden.', 'problem');
      });
  }, [client, token, garden, hasMarks, setStatus]);

  /** A typed moment, or back to now when the field is emptied. */
  const setSeenAt = useCallback((value: string) => setSeen(value === '' ? null : value), []);

  /** The next click on the plan marks this element's shadow edge. */
  const arm = useCallback(
    (elementId: number) => {
      setTarget(elementId);
      setTool('shadowmark');
    },
    [setTool],
  );

  /** Put the mark down unplaced. */
  const disarm = useCallback(() => {
    setTarget(null);
    setTool(null);
  }, [setTool]);

  /** Keep the mark the click placed, read against the model, and say what it found. */
  const place = useCallback(
    (x: number, y: number) => {
      if (target === null) return;
      const seen = (seenAt === null ? null : localToIso(seenAt)) ?? new Date().toISOString();
      void run('Schattenkante markieren', async () => {
        const made = await client.markShadow(token, { element_id: target, x, y, seen_at: seen });
        asked.current += 1;
        setMarks((list) => [...list, made]);
        setStatus(readingWords(made));
      });
    },
    [client, token, target, seenAt, run, setStatus],
  );

  const remove = useCallback(
    (markId: number) => {
      void run('Markierung löschen', async () => {
        await client.forgetShadowMark(token, markId);
        asked.current += 1;
        setMarks((list) => list.filter((mark) => mark.mark_id !== markId));
      });
    },
    [client, token, run],
  );

  return { marks, target, seenAt, setSeenAt, arm, disarm, place, remove };
}

export type ShadowMarks = ReturnType<typeof useShadowMarks>;
