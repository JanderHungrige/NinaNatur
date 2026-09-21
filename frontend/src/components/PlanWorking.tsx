import { Working } from './Working';

/**
 * Over the plan while its shade is computed (doc 65).
 *
 * The rebuild is the longest wait in the garden — terrain, the buildings, the
 * laser points, then the light, 13 s for a garden of 87 elements — and until
 * now the plan sat perfectly still through it. A band of light sweeps across
 * the drawing, and the words name the steps without claiming to know which one
 * is running: the server says when it is done, never how far along it is.
 *
 * Laid over the plan and never in its way: it takes no pointer, so the plan
 * can still be moved and looked at while it waits.
 */
export function PlanWorking() {
  return (
    <div className="plan-working" data-testid="plan-working">
      <Working
        className="plan-working__note"
        label="Schatten wird berechnet — Gelände, Gebäude, Laserdaten, Licht…"
      />
    </div>
  );
}
