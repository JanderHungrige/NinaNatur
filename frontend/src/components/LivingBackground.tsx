/** Where each drifting thing starts, how long it takes, and how big it is. */
const DRIFTERS = [
  { left: '6%', delay: '0s', duration: '34s', scale: 1, tilt: -12 },
  { left: '19%', delay: '-11s', duration: '41s', scale: 0.7, tilt: 24 },
  { left: '33%', delay: '-22s', duration: '29s', scale: 1.2, tilt: 8 },
  { left: '48%', delay: '-6s', duration: '46s', scale: 0.85, tilt: -30 },
  { left: '62%', delay: '-30s', duration: '33s', scale: 1.05, tilt: 16 },
  { left: '77%', delay: '-17s', duration: '38s', scale: 0.75, tilt: -20 },
  { left: '91%', delay: '-25s', duration: '43s', scale: 1.1, tilt: 30 },
];

/**
 * Leaves drifting behind the front door.
 *
 * CSS transforms and nothing else — no `requestAnimationFrame`, which on a
 * landing page runs until the tab is closed. Transforms are composited, so
 * seven of these cost nothing measurable.
 *
 * Negative delays start each one part-way through its journey, so the page does
 * not open with all seven lined up at the top.
 *
 * The whole thing is decoration: `aria-hidden`, behind the content, and low
 * enough in contrast that the words in front stay the thing you read. It stops
 * entirely under `prefers-reduced-motion` — feature 41 promised that, and this
 * is the first thing on the site that actually moves.
 */
export function LivingBackground() {
  return (
    <div className="living" aria-hidden="true" data-testid="living-background">
      {DRIFTERS.map((drifter) => (
        <span
          key={drifter.left}
          className="living__leaf"
          style={{
            left: drifter.left,
            animationDelay: drifter.delay,
            animationDuration: drifter.duration,
            ['--leaf-scale' as string]: String(drifter.scale),
            ['--leaf-tilt' as string]: `${drifter.tilt}deg`,
          }}
        >
          <svg viewBox="0 0 24 24" focusable="false">
            {/* A leaf: two arcs and a midrib, which is as much as reads at
                this size. */}
            <path d="M12 2 C 20 8, 20 16, 12 22 C 4 16, 4 8, 12 2 Z" />
            <path className="living__rib" d="M12 4 V 20" />
          </svg>
        </span>
      ))}
    </div>
  );
}
