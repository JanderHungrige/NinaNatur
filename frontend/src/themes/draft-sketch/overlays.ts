/*
 * The shape of `generated/rules.ts` (doc 97): what one of his symbols draws
 * along a shape rather than inside it, in metres, bottom first. The converter
 * writes the data; this is what the plan reads it as.
 */

/** His "Random" waveform: a wander of up to `amplitude` about once a `period`. */
export interface Wave {
  amplitude: number;
  period: number;
  seed: number;
}

interface Painted {
  colour: string;
  opacity: number;
}

/** The shape again, moved, under everything: a drop shadow. */
export interface Shadow extends Painted {
  kind: 'shadow';
  /** Garden metres, y north. */
  dx: number;
  dy: number;
  wave: Wave | null;
}

/** A line along the outline: his ink, solid — or along the outline drawn
 *  smaller about its middle (`scale`), as the rings inside his Tree 2. */
export interface Ink extends Painted {
  kind: 'ink';
  width: number;
  wave: Wave | null;
  dashes: readonly number[] | null;
  scale?: number;
}

/** A broad stroke just inside the outline: a rim, as round his water. */
export interface Band extends Painted {
  kind: 'band';
  width: number;
  /** How far inside the outline the band's middle runs. */
  inset: number;
  wave: Wave | null;
}

/** Every edge drawn on past its corners. */
export interface Overshoot extends Painted {
  kind: 'overshoot';
  width: number;
  length: number;
}

/** Short strokes every `spacing` just inside the outline, at `angle` degrees
 *  to it; swelling and shrinking through `sizes`, on the outline drawn smaller
 *  (`scale`), or only on the edges that face `facing` — the side in shade. */
export interface Ticks extends Painted {
  kind: 'ticks';
  width: number;
  length: number;
  spacing: number;
  inset: number;
  angle: number;
  sizes?: readonly number[];
  scale?: number;
  facing?: { x: number; y: number };
}

/** One of his marks at the shape's middle, through the mask of its image. */
export interface Centre extends Painted {
  kind: 'centre';
  mask: string;
  width: number;
  height: number;
  /** Degrees, clockwise as SVG turns. */
  rotation: number;
}

/** A colour ramp over the whole shape: `url(#…)` of a gradient in his defs. */
export interface Wash {
  kind: 'wash';
  fill: string;
}

/** A stroke along an element's line, `offset` to its left (negative: right). */
export interface LineInk extends Painted {
  kind: 'line-ink';
  width: number;
  offset: number;
  wave: Wave | null;
}

/** One of his images every `spacing` along a line, from `start`, turned
 *  `rotation` degrees from it (counter-clockwise, y north); swelling through
 *  `sizes`, straying up to `jitter` off the line. */
export interface LineMarks extends Painted {
  kind: 'line-marks';
  mask: string;
  /** His image, by its key in the generated symbols' `IMAGE`. */
  image: string;
  width: number;
  height: number;
  rotation: number;
  spacing: number;
  start: number;
  seed: number;
  sizes?: readonly number[];
  jitter?: number;
}

/** A square every `spacing` along a line: his fence's posts. */
export interface LineBoxes extends Painted {
  kind: 'line-boxes';
  size: number;
  spacing: number;
  start: number;
}

/** One of his images at each end of a line. */
export interface LineEnds extends Painted {
  kind: 'line-ends';
  mask: string;
  image: string;
  width: number;
  height: number;
  rotation: number;
}

/** What is drawn along an element's own line rather than round its outline (doc 98). */
export type LineOverlay = LineInk | LineMarks | LineBoxes | LineEnds;

/** The roof's lines, as the server's roof model gives them (doc 98). */
export interface RoofLines extends Painted {
  kind: 'roof';
  width: number;
  wave: Wave | null;
}

/** The outline again, `inset` inside itself: a raised bed's second edge. */
export interface Inner extends Painted {
  kind: 'inner';
  width: number;
  inset: number;
  wave: Wave | null;
}

export type Overlay = Shadow | Ink | Band | Overshoot | Ticks | Centre | Wash | RoofLines | Inner
  | LineOverlay;
