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

/** A line along the outline: his ink, solid. */
export interface Ink extends Painted {
  kind: 'ink';
  width: number;
  wave: Wave | null;
  dashes: readonly number[] | null;
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

/** Short strokes every `spacing` just inside the outline, at `angle` degrees to it. */
export interface Ticks extends Painted {
  kind: 'ticks';
  width: number;
  length: number;
  spacing: number;
  inset: number;
  angle: number;
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

export type Overlay = Shadow | Ink | Band | Overshoot | Ticks | Centre | Wash;
