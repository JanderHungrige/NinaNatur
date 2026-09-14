import {
  type FocusEvent,
  type KeyboardEvent,
  type RefObject,
  type UIEvent,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';

import { focusLost, holdsFocus } from '../suggestions/focus';
import { rowsPerPage, scrollToShow, visibleRange } from '../suggestions/window';
import { hasExtraLine, type Suggestion, SuggestionRow } from './SuggestionRow';

/** Sizes assumed until the window has measured itself — and in jsdom, which lays nothing out. */
const ASSUMED_VIEWPORT_PX = 416;
const ASSUMED_ROW_PX = 60;

type Step = (index: number, page: number, count: number) => number;

/** The keys that move the list's one tab stop (doc 90, rule 4). */
const STEPS: Record<string, Step> = {
  ArrowDown: (index) => index + 1,
  ArrowUp: (index) => index - 1,
  PageDown: (index, page) => index + page,
  PageUp: (index, page) => index - page,
  Home: () => 0,
  End: (_index, _page, count) => count - 1,
};

interface Props {
  items: Suggestion[];
  /** The list's name, as a screen reader announces it. */
  label: string;
  busy: boolean;
  onPlant: (taxonId: number, name: string) => Promise<void>;
  onShowInfo: (taxonId: number, name: string, colour: string | null) => void;
  /** Sizes to use instead of measured ones — for tests, as jsdom lays nothing out. */
  viewportPx?: number;
  rowPx?: number;
}

interface Measured {
  viewport: number;
  row: number;
}

/** The window's height and one row's, measured again whenever the window is resized. */
function useMeasured(scroller: RefObject<HTMLDivElement | null>, shape: string): Measured {
  const [measured, setMeasured] = useState<Measured>({ viewport: 0, row: 0 });
  useLayoutEffect(() => {
    const element = scroller.current;
    if (element === null) return undefined;
    const measure = () => {
      const row = element.querySelector('li')?.getBoundingClientRect().height ?? 0;
      const next = { viewport: element.clientHeight, row };
      setMeasured((was) => (was.viewport === next.viewport && was.row === next.row ? was : next));
    };
    measure();
    if (typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [scroller, shape]);
  return measured;
}

/**
 * The list's one tab stop and the scroll that keeps it in view, moved together.
 * The row about to take the focus is scrolled into the window first, so it is
 * in the document when it is focused; and a focused row that leaves the list
 * hands the focus to the row that takes its place (doc 90, rules 4 and 10).
 */
function useRovingStop(scroller: RefObject<HTMLDivElement | null>, count: number, viewport: number, row: number) {
  const [top, setTop] = useState(0);
  const [current, setCurrent] = useState(0);
  const pending = useRef<number | null>(null);
  const stop = Math.max(Math.min(current, count - 1), 0);
  const shownTop = Math.min(top, Math.max(count * row - viewport, 0));
  const hadFocus = holdsFocus(scroller.current);
  const rowAt = (index: number) =>
    scroller.current?.querySelector<HTMLElement>(`li[data-index="${index}"]`) ?? null;

  useLayoutEffect(() => {
    const wanted = pending.current ?? (hadFocus && focusLost() ? stop : null);
    pending.current = null;
    if (wanted !== null) rowAt(wanted)?.focus();
  });

  const moveTo = (index: number) => {
    const next = scrollToShow(index, shownTop, viewport, row);
    if (scroller.current !== null) scroller.current.scrollTop = next;
    setTop(next);
    setCurrent(index);
    const shown = rowAt(index);
    if (shown !== null) shown.focus();
    else pending.current = index;
  };

  return {
    stop,
    top: shownTop,
    onScroll: (event: UIEvent<HTMLDivElement>) => setTop(event.currentTarget.scrollTop),
    onKeyDown: (event: KeyboardEvent<HTMLUListElement>) => {
      const step = STEPS[event.key];
      if (step === undefined || count === 0 || event.altKey || event.ctrlKey || event.metaKey) return;
      event.preventDefault();
      moveTo(Math.min(Math.max(step(stop, rowsPerPage(viewport, row), count), 0), count - 1));
    },
    onFocus: (event: FocusEvent<HTMLUListElement>) => {
      const owner = (event.target as Element).closest<HTMLElement>('li[data-index]');
      if (owner !== null) setCurrent(Number(owner.dataset.index));
    },
  };
}

/**
 * A list that shows a window of its rows (doc 90): only the rows in view and
 * five either side are in the document, the rest of the list is height, and
 * one tab stop reaches every row. Rows are keyed by species, so a list fetched
 * again keeps its place.
 */
export function SuggestionWindow({ items, label, busy, onPlant, onShowInfo, viewportPx, rowPx }: Props) {
  const scroller = useRef<HTMLDivElement>(null);
  const count = items.length;
  const extraLine = items.some(hasExtraLine);
  const measured = useMeasured(scroller, `${count > 0}:${extraLine}`);
  const viewport = viewportPx ?? (measured.viewport > 0 ? measured.viewport : ASSUMED_VIEWPORT_PX);
  const row = rowPx ?? (measured.row > 0 ? measured.row : ASSUMED_ROW_PX);
  const { stop, top, onScroll, onKeyDown, onFocus } = useRovingStop(scroller, count, viewport, row);

  if (count === 0) return null;
  const { start, end } = visibleRange(top, viewport, row, count);
  const shown = Array.from({ length: end - start }, (_, i) => start + i);
  // The tab stop stays in the document while the list is scrolled away from it.
  if (stop < start) shown.unshift(stop);
  if (stop >= end) shown.push(stop);

  return (
    <div className="suggestion-window" ref={scroller} onScroll={onScroll}>
      <ul
        role="list"
        aria-label={label}
        className="suggestion-window__list"
        style={{ height: count * row }}
        onKeyDown={onKeyDown}
        onFocus={onFocus}
      >
        {shown.map((index) => {
          const item = items[index];
          return item === undefined ? null : (
            <SuggestionRow
              key={item.taxon_id}
              item={item}
              index={index}
              setsize={count}
              top={index * row}
              tabbable={index === stop}
              extraLine={extraLine}
              busy={busy}
              onPlant={onPlant}
              onShowInfo={onShowInfo}
            />
          );
        })}
      </ul>
    </div>
  );
}
