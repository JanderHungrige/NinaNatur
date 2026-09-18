import { usePlanTheme } from '../themes/context';

/**
 * Whose drawing style the plan is in, in the words its author agreed to
 * (doc 97; THIRD_PARTY.md) — beneath the plan whenever it is drawn in it, a
 * caption rather than a label on the drawing: in full, it would cover a third
 * of a phone's plan (doc 98). Nothing for a theme of our own.
 */
export function PlanCredit() {
  const { credit } = usePlanTheme();
  return credit === undefined ? null : <p className="plan-credit">{credit}</p>;
}
