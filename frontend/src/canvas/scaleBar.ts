/*
 * The plan's scale bar (doc 98): a length a person reads — 1, 2 or 5 times a
 * power of ten — drawn exactly as long as that length is on the screen now.
 * A bar that stayed one length while the plan zoomed would be a label that
 * lies.
 */

export interface ScaleBar {
  metres: number;
  pixels: number;
}

const STEPS = [1, 2, 5] as const;

/** The shortest readable length at least `minPixels` long at this scale. */
export function scaleBar(metresPerPixel: number, minPixels: number): ScaleBar {
  const wanted = metresPerPixel * minPixels;
  let power = 10 ** Math.floor(Math.log10(wanted));
  for (;;) {
    for (const step of STEPS) {
      const metres = step * power;
      if (metres >= wanted - 1e-12) return { metres, pixels: metres / metresPerPixel };
    }
    power *= 10;
  }
}
