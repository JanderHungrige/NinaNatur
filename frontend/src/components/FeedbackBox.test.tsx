import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { FeedbackQuestions } from '../api/client';
import { FeedbackBox } from './FeedbackBox';

const QUESTIONS: FeedbackQuestions = {
  bug: [
    { key: 'doing', label: 'Was wolltest du tun?', hint: 'z. B. ein Beet', required: true },
    { key: 'happened', label: 'Was ist passiert?', hint: 'was du sahst', required: true },
    { key: 'steps', label: 'Wie kommt man dahin?', hint: 'optional', required: false },
  ],
  idea: [
    { key: 'wish', label: 'Was möchtest du können?', hint: 'die Sache', required: true },
    { key: 'why', label: 'Was wäre leichter?', hint: 'wofür', required: true },
    { key: 'today', label: 'Wie behilfst du dir?', hint: 'optional', required: false },
  ],
};

function show(props: Partial<Parameters<typeof FeedbackBox>[0]> = {}) {
  const onSend = vi.fn().mockResolvedValue('Danke — ist eingetragen.');
  render(
    <FeedbackBox
      questions={QUESTIONS}
      onSend={onSend}
      onClose={vi.fn()}
      {...props}
    />,
  );
  return { onSend };
}

function answer(label: string | RegExp, text: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value: text } });
}

describe('FeedbackBox', () => {
  it('asks the questions the server gave, not its own', () => {
    // Two copies of the questions is how the heading in the filed issue ends
    // up disagreeing with the question that produced the answer under it.
    show();
    expect(screen.getByLabelText(/Was wolltest du tun/)).toBeDefined();
    expect(screen.getByLabelText(/Was ist passiert/)).toBeDefined();
  });

  it('switches to the other set of questions', () => {
    show();
    fireEvent.click(screen.getByRole('button', { name: /wünsche mir/ }));

    expect(screen.getByLabelText(/Was möchtest du können/)).toBeDefined();
    expect(screen.queryByLabelText(/Was wolltest du tun/)).toBeNull();
  });

  it('will not send until the required questions are answered', () => {
    show();
    const send = screen.getByRole('button', { name: 'Abschicken' });
    expect(send.hasAttribute('disabled')).toBe(true);

    answer(/Was wolltest du tun/, 'Ein Beet einzeichnen');
    expect(send.hasAttribute('disabled')).toBe(true);

    answer(/Was ist passiert/, 'Nichts');
    expect(send.hasAttribute('disabled')).toBe(false);
  });

  it('sends the answers under the keys the server asked with', async () => {
    const { onSend } = show();
    answer(/Was wolltest du tun/, 'Ein Beet einzeichnen');
    answer(/Was ist passiert/, 'Der Plan blieb weiß');
    fireEvent.click(screen.getByRole('button', { name: 'Abschicken' }));

    await waitFor(() =>
      expect(onSend).toHaveBeenCalledWith('bug', {
        doing: 'Ein Beet einzeichnen',
        happened: 'Der Plan blieb weiß',
      }),
    );
  });

  it('thanks only after the server has it', async () => {
    // Saying "danke" first is how a failed request gets mistaken for a
    // delivered bug report — the same mistake the colour note made.
    let settle: (message: string) => void = () => undefined;
    const onSend = vi.fn(
      () => new Promise<string>((resolve) => { settle = resolve; }),
    );
    show({ onSend });
    answer(/Was wolltest du tun/, 'a');
    answer(/Was ist passiert/, 'b');
    fireEvent.click(screen.getByRole('button', { name: 'Abschicken' }));

    expect(screen.queryByText(/eingetragen/)).toBeNull();
    settle('Danke — ist eingetragen.');
    await waitFor(() => expect(screen.getByText(/eingetragen/)).toBeDefined());
  });

  it('says what went wrong and keeps what was typed', async () => {
    const onSend = vi.fn().mockRejectedValue(new Error('429: zu viele'));
    show({ onSend });
    answer(/Was wolltest du tun/, 'Ein Beet einzeichnen');
    answer(/Was ist passiert/, 'Nichts');
    fireEvent.click(screen.getByRole('button', { name: 'Abschicken' }));

    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('429'));
    expect(screen.getByLabelText(/Was wolltest du tun/)).toHaveProperty(
      'value',
      'Ein Beet einzeichnen',
    );
  });

  it('warns that the tracker is public before anything is sent', () => {
    // Afterwards is too late for somebody who has just pasted a password.
    show();
    expect(screen.getByText(/öffentlich/)).toBeDefined();
  });

  it('waits rather than showing an empty form', () => {
    show({ questions: null });
    expect(screen.getByText('Wird geladen…')).toBeDefined();
    expect(screen.getByRole('button', { name: 'Abschicken' }).hasAttribute('disabled'))
      .toBe(true);
  });

  it('closes on Escape', () => {
    const onClose = vi.fn();
    show({ onClose });
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});
