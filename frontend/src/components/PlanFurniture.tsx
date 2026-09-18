import { usePlanTheme } from '../themes/context';

interface Props {
  metresPerPixel: number;
  title: string;
  updatedAt: string | null;
}

/**
 * The plan's north arrow, scale bar and title block, when its theme draws
 * them (doc 98) — in the plan's corner, never in the way of a click.
 */
export function PlanFurniture({ metresPerPixel, title, updatedAt }: Props) {
  const { Furniture } = usePlanTheme();
  if (Furniture === undefined) return null;
  return <Furniture metresPerPixel={metresPerPixel} title={title} updatedAt={updatedAt} />;
}
