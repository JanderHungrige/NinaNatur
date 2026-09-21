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
 * What the details are about (doc 88): the way back, its name as the view's
 * heading, and one line saying what it is.
 *
 * The way back comes first and stays in sight while the view scrolls: it is the
 * main route back to the garden, and as a grey underlined link under the title
 * it read as a footnote and scrolled away with the list (owner's check,
 * 2026-09-21). It is a sibling of the subject rather than inside it, because a
 * sticky box sticks only within its parent — inside this one it would have left
 * with the title. The arrow is decoration: the button's name stays its words.
 *
 * Two shapes lying on top of each other take the same click; the name and the
 * area say which one is being described before anything is changed. The heading
 * takes the focus when the view changes under a keyboard that was in the
 * details, which is why it can be focused without being in the tab order.
 */
export function InspectorSubject({ title, detail, back }: Props) {
  return (
    <>
      <button type="button" className="inspector__back" onClick={back.onBack}>
        <span aria-hidden="true">←</span> {back.label}
      </button>
      <div className="inspector__subject">
        <h2 className="inspector__title" tabIndex={-1} data-view-heading>
          {title}
        </h2>
        <p className="hint inspector__detail">{detail}</p>
      </div>
    </>
  );
}
