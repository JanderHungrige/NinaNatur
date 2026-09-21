import { useCallback, useEffect, useRef, useState } from 'react';

import type { GardenOut, NinaNaturClient } from '../api/client';
import { useGarden } from '../garden/useGarden';
import { useRemembered } from '../useRemembered';
import type { PlanChoice } from '../themes/usePageTheme';
import type { Status } from '../useStatus';
import type { Snap } from '../workspace/sheet';
import { useShortcutHelp } from '../workspace/useShortcutHelp';
import type { AccountInfo } from './AccountPanel';
import { BloomPlayer } from './BloomPlayer';
import { BloomTimeline } from './BloomTimeline';
import { GardenId } from './GardenId';
import { Inspector } from './Inspector';
import { InspectorPanels } from './InspectorPanels';
import { PlanArea } from './PlanArea';
import { ShortcutHelp } from './ShortcutHelp';
import { SiteHeader, type SiteProps } from './SiteHeader';
import { Skeleton } from './Skeleton';
import { ThemePicker } from './ThemePicker';
import { TimelineDock } from './TimelineDock';
import { ToolRail } from './ToolRail';

/** Where the three columns start: rail, a 40rem plan, and the details (doc 87).
 *  Below it the details are a sheet from below (doc 91). */
const WORKSPACE_QUERY = '(min-width: 66rem)';

/** Whether a media query matches now, and again whenever that changes. */
function useMatches(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia?.(query).matches ?? false);

  useEffect(() => {
    // Guarded like usePrefersReducedMotion: jsdom has no matchMedia unless a
    // test provides one.
    const list = window.matchMedia?.(query);
    if (list === undefined) return undefined;
    const onChange = (event: MediaQueryListEvent) => setMatches(event.matches);
    list.addEventListener('change', onChange);
    setMatches(list.matches);
    return () => list.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}

interface Props {
  client: NinaNaturClient;
  garden: GardenOut;
  setGarden: (garden: GardenOut) => void;
  status: Status;
  header: SiteProps;
  account: AccountInfo | null;
  /** Which style the plan is drawn in, and the choice of it (doc 100). */
  planStyle: PlanChoice;
  /** What to say once everything about the garden has arrived. */
  greeting: string;
}

/**
 * One open garden, as a workspace that fills the window (doc 87).
 *
 * Mounted with the garden's token as its key, so a different garden is a new
 * mount and nothing of the last one — selection, filters, tool, undo — carries
 * over. Nor does the sheet's height on a narrow window: every garden opens with
 * the details resting at a quarter (doc 91).
 */
export function GardenWorkspace({ client, garden, setGarden, status, header, account,
  planStyle, greeting }: Props) {
  const controller = useGarden(client, garden, setGarden, status, greeting);
  const { derived, elements, light, suggestions } = controller;
  const [wide, setWide] = useRemembered('ninanatur.inspector.wide', false);
  const [dockOpen, setDockOpen] = useRemembered('ninanatur.dock.open', true);
  // A phone's year starts folded: open, its table would lie over the plan.
  const [dockOpenNarrow, setDockOpenNarrow] = useRemembered('ninanatur.dock.open.narrow', false);
  const columns = useMatches(WORKSPACE_QUERY);
  const [snap, setSnap] = useState<Snap>('peek');
  const help = useShortcutHelp();
  const workspace = useRef<HTMLElement>(null);
  const month = suggestions.filters.floweringMonth ?? null;

  // A drag in progress goes straight to the stylesheet, so a moving finger
  // re-renders nothing; the plan waits for the height the drag comes to rest at.
  const onDrag = useCallback((fraction: number | null) => {
    const element = workspace.current;
    if (element === null) return;
    if (fraction === null) {
      element.style.removeProperty('--sheet-drag');
      delete element.dataset.dragging;
    } else {
      element.style.setProperty('--sheet-drag', String(fraction));
      element.dataset.dragging = '';
    }
  }, []);

  return (
    <>
      <SiteHeader
        {...header}
        busy={status.busy}
        working={status.working}
        more={
          <>
            <ThemePicker options={planStyle.options} chosen={planStyle.chosen}
                         onChoose={planStyle.choose} overridden={planStyle.overridden} />
            <button
              type="button"
              className="header-link"
              aria-pressed={light.shadeOn}
              disabled={light.rebuilding}
              title={derived.lightMap === null
                ? 'Berechnet Sonne und Schatten und legt sie über den Plan' : undefined}
              onClick={() => light.toggleOrCompute(derived.lightMap !== null)}
            >
              {'Sonne & Schatten'}
            </button>
            <button
              type="button"
              className="header-link"
              aria-haspopup="dialog"
              aria-keyshortcuts="?"
              onClick={help.show}
            >
              Tastenkürzel
            </button>
          </>
        }
      >
        {/* The page's title. Hidden, because the fold beside it already shows the name. */}
        <h1 className="sr-only">{garden.name}</h1>
        <GardenId
          token={garden.share_token}
          name={garden.name}
          latitude={garden.latitude}
          longitude={garden.longitude}
          onClaim={account !== null ? elements.claim : undefined}
        />
        <button
          type="button"
          className="header-link"
          aria-label="Letzte Änderung rückgängig"
          disabled={controller.undoDepth === 0}
          onClick={controller.undo}
        >
          ↶
        </button>
      </SiteHeader>

      <main
        id="main"
        ref={workspace}
        className={wide ? 'workspace workspace--wide' : 'workspace'}
        data-sheet={columns ? undefined : snap}
      >
        <ToolRail
          active={elements.tool}
          onPick={elements.setTool}
          busy={status.busy}
          orientation={columns ? 'vertical' : 'horizontal'}
        />
        <PlanArea garden={garden} controller={controller} />
        <Inspector wide={wide} onWide={setWide} sheet={columns ? undefined : { snap, onSnap: setSnap, onDrag }}>
          <InspectorPanels garden={garden} controller={controller} busy={status.busy} />
        </Inspector>
      </main>

      <TimelineDock
        open={columns ? dockOpen : dockOpenNarrow}
        onToggle={columns ? setDockOpen : setDockOpenNarrow}
        // The year only. The day plays in the sun panel, under the chip that
        // chose it (doc 65).
        player={<BloomPlayer month={month} onSelectMonth={suggestions.selectMonth} />}
      >
        {derived.timeline !== null ? (
          <BloomTimeline
            timeline={derived.timeline}
            forage={derived.forage}
            onToggleForage={derived.toggleForage}
            busy={status.busy}
            selectedMonth={month}
            onSelectMonth={suggestions.selectMonth}
          />
        ) : derived.loading ? (
          <Skeleton of="timeline" lines={4} />
        ) : null}
      </TimelineDock>

      <ShortcutHelp open={help.open} onClose={help.hide} />
    </>
  );
}
