import { createRoot } from 'react-dom/client';

import '../styles.css';
import { SHEET_GARDENS } from './gardens';
import { SheetCell } from './SheetCell';

/*
 * One cell of the plan's contact sheet per page load (doc 95): ?garden=&span=&sun=&w=&h=.
 * One per page because every pattern and filter id is global to a page, and
 * nine plans side by side would borrow each other's grid.
 */

const params = new URLSearchParams(window.location.search);
const entry = SHEET_GARDENS.find((g) => g.id === params.get('garden')) ?? SHEET_GARDENS[0]!;
const number = (key: string, fallback: number): number => {
  const value = Number(params.get(key) ?? fallback);
  return Number.isFinite(value) && value > 0 ? value : fallback;
};

const root = document.getElementById('sheet');
if (root === null) throw new Error('sheet.html has no #sheet');

const started = performance.now();
createRoot(root).render(
  <SheetCell entry={entry} spanM={number('span', 40)} sun={params.get('sun') === '1'}
             width={number('w', 360)} height={number('h', 270)} />,
);

// Ready once the fonts are in and two frames have been painted: a screenshot
// taken sooner can catch the plan half drawn. The time to here is the paint
// budget's measure.
void document.fonts.ready.then(() => {
  requestAnimationFrame(() => requestAnimationFrame(() => {
    (window as unknown as { paintMs: number }).paintMs = performance.now() - started;
    document.body.dataset.ready = 'yes';
  }));
});
