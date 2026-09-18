import { usePlanTheme } from '../themes/context';

/**
 * Whose drawing style the plan is in, in the words its author agreed to
 * (doc 97; THIRD_PARTY.md) — shown wherever the plan is drawn in it. Nothing
 * for a theme of our own.
 */
export function PlanCredit() {
  const { credit } = usePlanTheme();
  return credit === undefined ? null : <p className="plan-credit">{credit}</p>;
}
