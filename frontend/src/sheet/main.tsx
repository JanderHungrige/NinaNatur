import { createRoot } from 'react-dom/client';

import '../styles.css';
import { loadTheme, preloaded } from '../themes';
import { PlanThemeProvider } from '../themes/context';
import { SHEET_GARDENS } from './gardens';
import { SheetCell } from './SheetCell';
import { THEME_GARDENS } from './vocabulary';

/*
 * One cell of the plan's contact sheet per page load (doc 95):
 * ?garden=&span=&sun=&w=&h=, and &theme= for a theme other than Technisch
 * (doc 97), &x=&y= for a close-up (doc 98). One per page because every pattern and filter id is global to a
 * page, and nine plans side by side would borrow each other's grid.
 */

const params = new URLSearchParams(window.location.search);
const garden = [...SHEET_GARDENS, ...THEME_GARDENS].find((g) => g.id === params.get('garden'))
  ?? SHEET_GARDENS[0]!;
// &x=&y= looks somewhere else in the garden: a close-up, never part of the sheet.
const at = (key: 'x' | 'y') => (params.has(key) ? Number(params.get(key)) : garden.centre[key]);
const entry = { ...garden, centre: { x: at('x'), y: at('y') } };
const number = (key: string, fallback: number): number => {
  const value = Number(params.get(key) ?? fallback);
  return Number.isFinite(value) && value > 0 ? value : fallback;
};

const root = document.getElementById('sheet');
if (root === null) throw new Error('sheet.html has no #sheet');
const sheet = root;

// The theme and its images come first, and the clock starts after them: the
// paint budget measures drawing, not fetching.
void loadTheme(params.get('theme') ?? 'technisch').then(preloaded).then((theme) => {
  const started = performance.now();
  createRoot(sheet).render(
    <PlanThemeProvider theme={theme}>
      <SheetCell entry={entry} spanM={number('span', 40)} sun={params.get('sun') === '1'}
                 width={number('w', 360)} height={number('h', 270)} />
    </PlanThemeProvider>,
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
});
