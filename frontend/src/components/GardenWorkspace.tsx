import { useEffect, useState } from 'react';

import type { GardenOut, NinaNaturClient } from '../api/client';
import { useGarden } from '../garden/useGarden';
import { useRemembered } from '../useRemembered';
import type { Status } from '../useStatus';
import type { AccountInfo } from './AccountPanel';
import { BloomPlayer } from './BloomPlayer';
import { BloomTimeline } from './BloomTimeline';
import { GardenId } from './GardenId';
import { Inspector } from './Inspector';
import { InspectorPanels } from './InspectorPanels';
import { PlanArea } from './PlanArea';
import { SiteHeader, type SiteProps } from './SiteHeader';
import { TimelineDock } from './TimelineDock';
import { ToolRail } from './ToolRail';

/** Where the three columns start: rail, a 40rem plan, and the details (doc 87). */
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
  /** What to say once everything about the garden has arrived. */
  greeting: string;
}

/**
 * One open garden, as a workspace that fills the window (doc 87).
 *
 * Mounted with the garden's token as its key, so a different garden is a new
 * mount and nothing of the last one — selection, filters, tool, undo — carries
 * over.
 */
export function GardenWorkspace({ client, garden, setGarden, status, header, account, greeting }: Props) {
  const controller = useGarden(client, garden, setGarden, status, greeting);
  const { derived, elements, light, suggestions } = controller;
  const [wide, setWide] = useRemembered('ninanatur.inspector.wide', false);
  const [dockOpen, setDockOpen] = useRemembered('ninanatur.dock.open', true);
  const vertical = useMatches(WORKSPACE_QUERY);
  const month = suggestions.filters.floweringMonth ?? null;

  return (
    <>
      <SiteHeader {...header} busy={status.busy}>
        {/* The page's title. Hidden, because the fold beside it already shows the name. */}
        <h1 className="sr-only">{garden.name}</h1>
        <GardenId
          token={garden.share_token}
          name={garden.name}
          latitude={garden.latitude}
          longitude={garden.longitude}
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
        <button
          type="button"
          className="header-link"
          aria-pressed={light.shadeOn}
          disabled={derived.lightMap === null}
          onClick={() => light.toggleShade(!light.shadeOn)}
        >
          {'Sonne & Schatten'}
        </button>
      </SiteHeader>

      <main id="main" className={wide ? 'workspace workspace--wide' : 'workspace'}>
        <ToolRail
          active={elements.tool}
          onPick={elements.setTool}
          busy={status.busy}
          orientation={vertical ? 'vertical' : 'horizontal'}
        />
        <PlanArea garden={garden} controller={controller} />
        <Inspector wide={wide} onWide={setWide}>
          <InspectorPanels garden={garden} controller={controller} account={account} busy={status.busy} />
        </Inspector>
      </main>

      <TimelineDock
        open={dockOpen}
        onToggle={setDockOpen}
        player={
          <BloomPlayer
            month={month}
            onSelectMonth={suggestions.selectMonth}
            shadowDay={
              light.shadeOn && light.day !== null
                ? { frames: light.day.frames.length, frame: light.frame, onFrame: light.setFrame }
                : undefined
            }
          />
        }
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
        ) : null}
      </TimelineDock>
    </>
  );
}
