interface Props {
  title: string;
  /** What it is and what it covers, in one line. */
  detail: string;
  back: { label: string; onBack: () => void };
}

/** "6,0 m²", written as the element list writes it. */
export function squareMetres(area: number): string {
  return `${area.toFixed(1).replace('.', ',')} m²`;
}

/**
 * What the details are about (doc 88): its name as the view's heading, one line
 * saying what it is, and the way back.
 *
 * Two shapes lying on top of each other take the same click; the name and the
 * area say which one is being described before anything is changed. The heading
 * takes the focus when the view changes under a keyboard that was in the
 * details, which is why it can be focused without being in the tab order.
 */
export function InspectorSubject({ title, detail, back }: Props) {
  return (
    <div className="inspector__subject">
      <h2 className="inspector__title" tabIndex={-1} data-view-heading>
        {title}
      </h2>
      <p className="hint inspector__detail">{detail}</p>
      <button type="button" className="link-button inspector__back" onClick={back.onBack}>
        {back.label}
      </button>
    </div>
  );
}
