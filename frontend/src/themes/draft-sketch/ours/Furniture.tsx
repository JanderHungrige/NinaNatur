/**
 * Provenance: NinaNatur, in the style of Draft Sketch
 *
 * The plan's north arrow, scale bar and title block (doc 98), in his black ink
 * on his paper: a drawing has them, where the plan only ever said "N ↑". The
 * scale bar is exactly as long as the length it names, at every zoom.
 */
import { scaleBar } from '../../../canvas/scaleBar';
import type { FurnitureProps } from '../../types';

/** Never shorter than this on the screen, so it can be read and measured by. */
const BAR_MIN_PX = 56;

const metres = (value: number): string =>
  value >= 1000 ? `${(value / 1000).toLocaleString('de-DE')} km` : `${value.toLocaleString('de-DE')} m`;

function day(updatedAt: string | null): string | null {
  if (updatedAt === null) return null;
  const date = new Date(updatedAt);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleDateString('de-DE');
}

function North() {
  return (
    <svg className="plan-furniture__north" viewBox="0 0 24 38" width="24" height="38" aria-hidden="true">
      <path d="M12.4 36 C11.6 28 12.6 20 12 12" fill="none" stroke="#000" strokeWidth="1.6"
            strokeLinecap="round" />
      <path d="M12 2.5 L18.5 15 L12.2 11.6 L5.6 15.4 Z" fill="#000" />
      <text x="12" y="37.5" textAnchor="middle" fontSize="9" fontWeight="700" dy="-0.5"
            paintOrder="stroke" stroke="#fbfaf6" strokeWidth="3">N</text>
    </svg>
  );
}

function Bar({ metresPerPixel }: { metresPerPixel: number }) {
  const bar = scaleBar(metresPerPixel, BAR_MIN_PX);
  const run = Math.round(bar.pixels * 10) / 10;
  const half = run / 2;
  return (
    <div className="plan-furniture__scale" role="img" aria-label={`Maßstabsleiste: ${metres(bar.metres)}`}>
      <svg width={run + 8} height="24" viewBox={`-4 0 ${run + 8} 24`} aria-hidden="true">
        <rect x="0" y="12" width={half} height="4" fill="#000" />
        <rect x={half} y="12" width={half} height="4" fill="#fbfaf6" stroke="#000" strokeWidth="1" />
        <path d={`M0 9 V18 M${half} 11 V18 M${run} 9 V18`} stroke="#000" strokeWidth="1.2"
              strokeLinecap="round" />
        <text x="0" y="7" fontSize="8" textAnchor="middle">0</text>
        <text x={run} y="7" fontSize="8" textAnchor="middle">{metres(bar.metres)}</text>
      </svg>
    </div>
  );
}

export function DraftSketchFurniture({ metresPerPixel, title, updatedAt }: FurnitureProps) {
  const date = day(updatedAt);
  return (
    <figure className="plan-furniture">
      <North />
      <Bar metresPerPixel={metresPerPixel} />
      <figcaption className="plan-furniture__title">
        <strong>{title}</strong>
        {date !== null && <span>Stand {date}</span>}
      </figcaption>
    </figure>
  );
}
