import type React from 'react';

import type { Cluster } from '../canvas/clusters';

/** Ten drawable colours, as the plan paints them. */
export const SWATCH: Record<string, string> = {
  yellow: '#e8c33a',
  white: '#f2f0e6',
  pink: '#dd8fb2',
  violet: '#8f7fc4',
  blue: '#6f92cf',
  red: '#c9533f',
  orange: '#e08a3c',
  green: '#7aa05a',
  brown: '#8a6a4a',
  black: '#3b3b39',
};

interface Props {
  clusters: Cluster[];
  selectedPlantingId?: number | null;
  onSelectCluster?: ((plantingId: number) => void) | undefined;
  onGrabCluster?: ((plantingId: number, event: React.PointerEvent) => void) | undefined;
  /** The grid's current spacing in metres. Text is sized from it so a label
   *  stays legible at any zoom — the viewBox is in metres, so a fixed font
   *  size would be a fixed number of *metres* tall. */
  spacing?: number;
  onShowInfo?: ((taxonId: number, name: string) => void) | undefined;
}

/**
 * Every planting as a patch of dots.
 *
 * Grey unless it is in flower in the month being shown, so the plan answers
 * "how full is this bed" all year round. The colour band this replaces could
 * only ever show what was flowering *now* — an empty bed and a bed full of
 * leaves looked exactly alike — and it was a band, which says the bed is half
 * yellow and half blue when what is true is that some of the flowers are.
 *
 * Drawn on top of the beds and outside the wobble filter: a dot the size of a
 * blossom disappears under a displacement map meant for outlines.
 */
export function ClusterLayer({
  clusters,
  selectedPlantingId = null,
  onSelectCluster,
  onGrabCluster,
  spacing = 1,
  onShowInfo,
}: Props) {
  const selected = clusters.find((c) => c.plantingId === selectedPlantingId) ?? null;
  const interactive = onSelectCluster !== undefined || onGrabCluster !== undefined;

  return (
    <g className="blooms" aria-hidden={interactive ? undefined : true}>
      {clusters.map((cluster) => (
        <g
          key={cluster.plantingId}
          data-testid={`cluster-${cluster.plantingId}`}
          data-planting-id={cluster.plantingId}
          className={
            cluster.plantingId === selectedPlantingId
              ? 'cluster cluster--selected'
              : 'cluster'
          }
          role={onSelectCluster === undefined ? undefined : 'button'}
          tabIndex={onSelectCluster === undefined ? undefined : 0}
          aria-label={cluster.name}
          onPointerDown={
            onGrabCluster === undefined
              ? undefined
              : (event) => onGrabCluster(cluster.plantingId, event)
          }
          onClick={
            onSelectCluster === undefined
              ? undefined
              : (event) => {
                  // The bed underneath is a click target too, and a click that
                  // reaches both selects the bed and then the cluster, or the
                  // other way about depending on order. One of them has to win
                  // and it is the smaller thing, which is what was aimed at.
                  event.stopPropagation();
                  onSelectCluster(cluster.plantingId);
                }
          }
          onKeyDown={
            onSelectCluster === undefined
              ? undefined
              : (event) => {
                  if (event.key !== 'Enter' && event.key !== ' ') return;
                  event.preventDefault();
                  onSelectCluster(cluster.plantingId);
                }
          }
        >
          {/* What the pointer actually hits. Nearly invisible until this is the
              selected patch — chasing a two-centimetre dot with a mouse is not
              a gesture anybody can perform. */}
          <circle
            className="cluster__reach"
            cx={cluster.centre.x}
            cy={-cluster.centre.y}
            r={Math.max(cluster.radius, 0.35)}
          />
          {cluster.dots.map((dot, i) => (
            <circle
              key={i}
              className="bloom-dot"
              cx={dot.x}
              cy={-dot.y}
              r={dot.r}
              fill={
                cluster.colour === null
                  ? 'var(--ink-muted)'
                  : (SWATCH[cluster.colour] ?? 'var(--ink-muted)')
              }
            />
          ))}
          <title>{cluster.name}</title>
        </g>
      ))}

      {/* The name of the patch under the pointer's last click, written on the
          plan rather than in a panel across the page. Sized from the grid, so
          it stays the same size on screen however far the garden is zoomed. */}
      {selected !== null && (
        <g className="cluster-tag" data-testid="cluster-tag">
          <text
            className="cluster-tag__name"
            x={selected.centre.x}
            y={-(selected.centre.y + selected.radius) - spacing * 0.25}
            textAnchor="middle"
            fontSize={spacing * 0.42}
          >
            {selected.name}
          </text>
          {selected.taxonId !== null && onShowInfo !== undefined && (
            <g
              className="cluster-tag__info"
              role="button"
              tabIndex={0}
              aria-label={`Info zu ${selected.name}`}
              onClick={(event) => {
                event.stopPropagation();
                onShowInfo(selected.taxonId as number, selected.name);
              }}
              onKeyDown={(event) => {
                if (event.key !== 'Enter' && event.key !== ' ') return;
                event.preventDefault();
                onShowInfo(selected.taxonId as number, selected.name);
              }}
            >
              <circle
                cx={selected.centre.x}
                cy={-(selected.centre.y + selected.radius) - spacing * 0.85}
                r={spacing * 0.3}
              />
              <text
                x={selected.centre.x}
                y={-(selected.centre.y + selected.radius) - spacing * 0.72}
                textAnchor="middle"
                fontSize={spacing * 0.42}
              >
                i
              </text>
            </g>
          )}
        </g>
      )}
    </g>
  );
}
