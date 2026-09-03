import { useEffect, useId, useRef, useState } from 'react';

import type { FeedbackQuestion, FeedbackQuestions } from '../api/client';

type Kind = 'bug' | 'idea';

interface Props {
  /** What to ask, from the server. Null while it is still being fetched. */
  questions: FeedbackQuestions | null;
  onSend: (kind: Kind, answers: Record<string, string>) => Promise<string | null>;
  onClose: () => void;
}

const TABS: Array<[Kind, string]> = [
  ['bug', 'Etwas geht nicht'],
  ['idea', 'Ich wünsche mir etwas'],
];

/**
 * The feedback form.
 *
 * Guiding questions rather than one empty box, because "was ist kaputt" is
 * answered with "geht nicht" about half the time, and three specific questions
 * are what turn a report into something reproducible.
 *
 * The questions come from the server. It writes the issue from the same list,
 * so a heading there cannot end up disagreeing with the question that produced
 * the answer under it.
 */
export function FeedbackBox({ questions, onSend, onClose }: Props) {
  const [kind, setKind] = useState<Kind>('bug');
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [state, setState] = useState<'asking' | 'sending' | 'sent'>('asking');
  const [problem, setProblem] = useState<string | null>(null);
  const [thanks, setThanks] = useState<string | null>(null);
  const panel = useRef<HTMLDivElement>(null);
  const headingId = useId();

  useEffect(() => {
    panel.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const asked: FeedbackQuestion[] = questions?.[kind] ?? [];
  const missing = asked.some((q) => q.required && !(answers[q.key] ?? '').trim());

  const submit = async () => {
    setState('sending');
    setProblem(null);
    try {
      // Only once the server has it. Saying "danke" first is how a failed
      // request gets mistaken for a delivered report.
      setThanks(await onSend(kind, answers));
      setState('sent');
    } catch (error) {
      setProblem(error instanceof Error ? error.message : 'Senden fehlgeschlagen');
      setState('asking');
    }
  };

  return (
    <div
      className="panel feedback"
      role="dialog"
      aria-modal="false"
      aria-labelledby={headingId}
      tabIndex={-1}
      ref={panel}
    >
      <div className="feedback__head">
        <h2 id={headingId}>Rückmeldung</h2>
        <button type="button" className="link-button" onClick={onClose}>
          Schließen
        </button>
      </div>

      {state === 'sent' ? (
        <p className="feedback__thanks" role="status">
          {thanks ?? 'Danke.'}
        </p>
      ) : (
        <>
          <div className="feedback__kinds">
            {TABS.map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={value === kind ? 'chip chip--on' : 'chip'}
                aria-pressed={value === kind}
                onClick={() => setKind(value)}
              >
                {label}
              </button>
            ))}
          </div>

          {questions === null ? (
            <p className="hint">Wird geladen…</p>
          ) : (
            asked.map((question) => (
              <label key={question.key} className="feedback__field">
                {question.label}
                <textarea
                  rows={3}
                  value={answers[question.key] ?? ''}
                  onChange={(e) =>
                    setAnswers({ ...answers, [question.key]: e.target.value })
                  }
                />
                <span className="hint">{question.hint}</span>
              </label>
            ))
          )}

          {/* Said before sending, not after: the tracker is public, and
              somebody about to paste a password should read it first. */}
          <p className="hint feedback__notice">
            Landet öffentlich im Projekt-Tracker. Bitte nichts hineinschreiben,
            was niemand sonst lesen soll — der Link zu deinem Garten wird nicht
            mitgeschickt.
          </p>

          {problem !== null && (
            <p className="hint" role="alert">
              {problem}
            </p>
          )}

          <button
            type="button"
            disabled={missing || state === 'sending' || questions === null}
            onClick={() => void submit()}
          >
            {state === 'sending' ? 'Wird gesendet…' : 'Abschicken'}
          </button>
        </>
      )}
    </div>
  );
}
