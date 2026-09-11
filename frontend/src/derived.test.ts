import { describe, expect, it, vi } from 'vitest';

import type {
  BloomPalette,
  ImprovementsOut,
  LightMap,
  ScoreOut,
  Terrain,
  TimelineOut,
} from './api/client';
import { fetchDerived, type DerivedSetters, type DerivedSource } from './derived';

/** A promise the test answers when it chooses: how "at once" becomes checkable. */
function later<T>() {
  let answer!: (value: T) => void;
  let fail!: (reason: Error) => void;
  const promise = new Promise<T>((resolve, reject) => {
    answer = resolve;
    fail = reject;
  });
  return { promise, answer, fail };
}

function pending() {
  return {
    timeline: later<TimelineOut>(),
    score: later<ScoreOut>(),
    improvements: later<ImprovementsOut>(),
    bloom: later<BloomPalette>(),
    lightMap: later<LightMap | null>(),
    terrain: later<Terrain | null>(),
  };
}

type Pending = ReturnType<typeof pending>;

/** The six calls a garden's derived state needs, each recorded as it is made. */
function server(answers: Pending) {
  const asked: string[] = [];
  const ask = <T>(name: string, answer: Promise<T>) => {
    asked.push(name);
    return answer;
  };
  const spies = {
    timeline: vi.fn((_token: string, _weighted?: boolean) => ask('timeline', answers.timeline.promise)),
    score: vi.fn((_token: string) => ask('score', answers.score.promise)),
    improvements: vi.fn((_token: string) => ask('improvements', answers.improvements.promise)),
    bloom: vi.fn((_token: string) => ask('bloom', answers.bloom.promise)),
    lightMap: vi.fn((_token: string) => ask('lightMap', answers.lightMap.promise)),
    terrain: vi.fn((_token: string) => ask('terrain', answers.terrain.promise)),
  };
  return { client: spies as unknown as DerivedSource, asked, spies };
}

function screen() {
  return {
    timeline: vi.fn(),
    score: vi.fn(),
    improvements: vi.fn(),
    palette: vi.fn(),
    lightMap: vi.fn(),
    terrain: vi.fn(),
  } satisfies DerivedSetters;
}

const TIMELINE = { mode: 'forage' } as unknown as TimelineOut;
const SCORE = { score: 3.5 } as unknown as ScoreOut;
const IMPROVEMENTS = { current_score: 3.5 } as unknown as ImprovementsOut;
const PALETTE = { beds: {} } as unknown as BloomPalette;

/** Let every answer already given reach its `then`. */
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

function answerAll(answers: Pending): void {
  answers.timeline.answer(TIMELINE);
  answers.score.answer(SCORE);
  answers.improvements.answer(IMPROVEMENTS);
  answers.bloom.answer(PALETTE);
  answers.lightMap.answer(null);
  answers.terrain.answer(null);
}

describe('fetchDerived', () => {
  it('asks for all six before any one has answered', () => {
    // Opening a garden used to await each of these in turn: eight round trips,
    // one after another, on a connection that could carry them together.
    const { client, asked } = server(pending());
    void fetchDerived(client, 'token', true, screen());

    expect([...asked].sort()).toEqual(
      ['bloom', 'improvements', 'lightMap', 'score', 'terrain', 'timeline'],
    );
  });

  it('shows each answer as it arrives, not when the slowest one does', async () => {
    const answers = pending();
    const { client } = server(answers);
    const shown = screen();
    const done = fetchDerived(client, 'token', true, shown);

    answers.score.answer(SCORE);
    await settle();
    expect(shown.score).toHaveBeenCalledWith(SCORE);
    expect(shown.timeline).not.toHaveBeenCalled();

    answerAll(answers);
    await done;
    expect(shown.timeline).toHaveBeenCalledWith(TIMELINE);
    expect(shown.palette).toHaveBeenCalledWith(PALETTE);
    expect(shown.lightMap).toHaveBeenCalledWith(null);
  });

  it('keeps every answer that arrived when another one fails', async () => {
    // Asked one after another, a failed sun map also cost the bloom palette
    // behind it. Asked together, it costs only itself — and still says so.
    const answers = pending();
    const { client } = server(answers);
    const shown = screen();
    const done = fetchDerived(client, 'token', true, shown);

    answers.timeline.answer(TIMELINE);
    answers.score.answer(SCORE);
    answers.improvements.answer(IMPROVEMENTS);
    answers.bloom.answer(PALETTE);
    answers.terrain.answer(null);
    answers.lightMap.fail(new Error('Sonnenkarte: 503'));

    await expect(done).rejects.toThrow('503');
    await settle();
    expect(shown.timeline).toHaveBeenCalledWith(TIMELINE);
    expect(shown.palette).toHaveBeenCalledWith(PALETTE);
    expect(shown.lightMap).not.toHaveBeenCalled();
  });

  it('weights the bloom year as it was asked to', () => {
    const { client, spies } = server(pending());
    void fetchDerived(client, 'token', false, screen());

    expect(spies.timeline).toHaveBeenCalledWith('token', false);
  });
});
