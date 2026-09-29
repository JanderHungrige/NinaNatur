import { useState } from 'react';

import { usePlanTheme } from '../themes/context';

interface Props {
  metresPerPixel: number;
  title: string;
  updatedAt: string | null;
  /** Whether it can be put away: on the plan, not on the contact sheet. */
  closable?: boolean;
}

/**
 * The plan's north arrow, scale bar and title block, when its theme draws
 * them (doc 98) — in the plan's corner, never in the way of a click.
 *
 * It can be closed, and comes back with the next load of the page: a legend
 * that stayed away would be one somebody forgot they had closed (the owner,
 * 2026-09-28). Kept in the page, never in the browser's storage.
 */
export function PlanFurniture({ metresPerPixel, title, updatedAt, closable = true }: Props) {
  const { Furniture } = usePlanTheme();
  const [closed, setClosed] = useState(false);
  if (Furniture === undefined || closed) return null;
  return <Furniture metresPerPixel={metresPerPixel} title={title} updatedAt={updatedAt}
                    onClose={closable ? () => setClosed(true) : undefined} />;
}
