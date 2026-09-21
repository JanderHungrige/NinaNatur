/**
 * Provenance: Warren Davison (Draft Sketch)
 *
 * Generated from Draft_Sketch.stylx (sha256 4ef38ef8…) by
 * `python -m scripts.stylx_to_theme`. Do not edit: regenerate (doc 97).
 *
 * His images, each once and unchanged, and his symbols' fills as SVG
 * patterns. A tint is his colour through the image's alpha: what tinting
 * does to the white washes and black marks he tints.
 */
import ds_0b0e781b from './images/ds-0b0e781b.png';
import ds_1bb4640e from './images/ds-1bb4640e.png';
import ds_1eb5bff4 from './images/ds-1eb5bff4.png';
import ds_1f0fe8f5 from './images/ds-1f0fe8f5.png';
import ds_57481b74 from './images/ds-57481b74.png';
import ds_67b90642 from './images/ds-67b90642.png';
import ds_6c7f0598 from './images/ds-6c7f0598.png';
import ds_9c8ef47c from './images/ds-9c8ef47c.png';
import ds_d8f827fc from './images/ds-d8f827fc.png';
import ds_df4f3810 from './images/ds-df4f3810.png';
import ds_f08c1e65 from './images/ds-f08c1e65.png';

/** Every image the patterns draw, for whoever must wait for them to load. */
export const IMAGES: readonly string[] = [
  ds_0b0e781b,
  ds_1bb4640e,
  ds_1eb5bff4,
  ds_1f0fe8f5,
  ds_57481b74,
  ds_67b90642,
  ds_6c7f0598,
  ds_9c8ef47c,
  ds_d8f827fc,
  ds_df4f3810,
  ds_f08c1e65,
];

/** His images by key, for marks laid along a line (doc 98). */
export const IMAGE: Readonly<Record<string, string>> = {
  'ds-0b0e781b': ds_0b0e781b,
  'ds-1bb4640e': ds_1bb4640e,
  'ds-1eb5bff4': ds_1eb5bff4,
  'ds-1f0fe8f5': ds_1f0fe8f5,
  'ds-57481b74': ds_57481b74,
  'ds-67b90642': ds_67b90642,
  'ds-6c7f0598': ds_6c7f0598,
  'ds-9c8ef47c': ds_9c8ef47c,
  'ds-d8f827fc': ds_d8f827fc,
  'ds-df4f3810': ds_df4f3810,
  'ds-f08c1e65': ds_f08c1e65,
};

/** His marks as markup: parsed by the browser in one go (see ../Defs.tsx). */
export const SYMBOLS = `
<mask id="ds-0b0e781b-mask" maskContentUnits="objectBoundingBox" mask-type="alpha"><image href="${ds_0b0e781b}" width="1" height="1" preserveAspectRatio="none"/></mask>
<mask id="ds-1bb4640e-mask" maskContentUnits="objectBoundingBox" mask-type="alpha"><image href="${ds_1bb4640e}" width="1" height="1" preserveAspectRatio="none"/></mask>
<mask id="ds-1eb5bff4-mask" maskContentUnits="objectBoundingBox" mask-type="alpha"><image href="${ds_1eb5bff4}" width="1" height="1" preserveAspectRatio="none"/></mask>
<mask id="ds-1f0fe8f5-mask" maskContentUnits="objectBoundingBox" mask-type="alpha"><image href="${ds_1f0fe8f5}" width="1" height="1" preserveAspectRatio="none"/></mask>
<mask id="ds-57481b74-mask" maskContentUnits="objectBoundingBox" mask-type="alpha"><image href="${ds_57481b74}" width="1" height="1" preserveAspectRatio="none"/></mask>
<mask id="ds-67b90642-mask" maskContentUnits="objectBoundingBox" mask-type="alpha"><image href="${ds_67b90642}" width="1" height="1" preserveAspectRatio="none"/></mask>
<mask id="ds-9c8ef47c-mask" maskContentUnits="objectBoundingBox" mask-type="alpha"><image href="${ds_9c8ef47c}" width="1" height="1" preserveAspectRatio="none"/></mask>
<mask id="ds-d8f827fc-mask" maskContentUnits="objectBoundingBox" mask-type="alpha"><image href="${ds_d8f827fc}" width="1" height="1" preserveAspectRatio="none"/></mask>
<mask id="ds-f08c1e65-mask" maskContentUnits="objectBoundingBox" mask-type="alpha"><image href="${ds_f08c1e65}" width="1" height="1" preserveAspectRatio="none"/></mask>
<radialGradient id="ds-tree-near-ramp-0" cx="0.5" cy="0.5" r="0.5">
<stop offset="0" stop-color="#728944"/>
<stop offset="0.95" stop-color="#5c8944" stop-opacity="0"/>
</radialGradient>
<linearGradient id="ds-tree-near-ramp-1" x1="0.146" y1="0.146" x2="0.854" y2="0.854">
<stop offset="0" stop-color="#b4d79e" stop-opacity="0.85"/>
<stop offset="0.95" stop-color="#5c8944" stop-opacity="0"/>
</linearGradient>
<linearGradient id="ds-tree-mid-ramp-0" x1="0.146" y1="0.146" x2="0.854" y2="0.854">
<stop offset="0" stop-color="#b4d79e"/>
<stop offset="0.95" stop-color="#5c8944" stop-opacity="0"/>
</linearGradient>
<linearGradient id="ds-tree-far-ramp-0" x1="0.146" y1="0.146" x2="0.854" y2="0.854">
<stop offset="0" stop-color="#b4d79e"/>
<stop offset="0.95" stop-color="#5c8944" stop-opacity="0"/>
</linearGradient>
<radialGradient id="ds-shrub-near-ramp-0" cx="0.5" cy="0.5" r="0.5">
<stop offset="0" stop-color="#5c8944"/>
<stop offset="0.95" stop-color="#5c892f" stop-opacity="0.2"/>
</radialGradient>
<linearGradient id="ds-shrub-near-ramp-1" x1="0.146" y1="0.146" x2="0.854" y2="0.854">
<stop offset="0" stop-color="#b0e58f" stop-opacity="0.85"/>
<stop offset="0.95" stop-color="#5c8944" stop-opacity="0"/>
</linearGradient>
<radialGradient id="ds-shrub-mid-ramp-0" cx="0.5" cy="0.5" r="0.5">
<stop offset="0" stop-color="#5c8944"/>
<stop offset="0.95" stop-color="#5c892f" stop-opacity="0.2"/>
</radialGradient>
<linearGradient id="ds-shrub-mid-ramp-1" x1="0.146" y1="0.146" x2="0.854" y2="0.854">
<stop offset="0" stop-color="#b0e58f" stop-opacity="0.85"/>
<stop offset="0.95" stop-color="#5c8944" stop-opacity="0"/>
</linearGradient>
<radialGradient id="ds-shrub-far-ramp-0" cx="0.5" cy="0.5" r="0.5">
<stop offset="0" stop-color="#5c8944"/>
<stop offset="0.95" stop-color="#5c892f" stop-opacity="0.2"/>
</radialGradient>
<linearGradient id="ds-shrub-far-ramp-1" x1="0.146" y1="0.146" x2="0.854" y2="0.854">
<stop offset="0" stop-color="#b0e58f" stop-opacity="0.85"/>
<stop offset="0.95" stop-color="#5c8944" stop-opacity="0"/>
</linearGradient>
<pattern id="ds-building-near-tile" width="17.639" height="17.639" patternUnits="userSpaceOnUse">
<rect width="17.639" height="17.639" fill="#ffffff"/>
</pattern>
<pattern id="ds-building-near" width="17.639" height="17.639" patternUnits="userSpaceOnUse"><rect width="17.639" height="17.639" fill="url(#ds-building-near-tile)"/></pattern>
<pattern id="ds-building-mid-tile" width="17.639" height="17.639" patternUnits="userSpaceOnUse">
<rect width="17.639" height="17.639" fill="#ffffff"/>
</pattern>
<pattern id="ds-building-mid" width="17.639" height="17.639" patternUnits="userSpaceOnUse"><rect width="17.639" height="17.639" fill="url(#ds-building-mid-tile)"/></pattern>
<pattern id="ds-building-far-tile" width="17.639" height="17.639" patternUnits="userSpaceOnUse">
<rect width="17.639" height="17.639" fill="#ffffff"/>
</pattern>
<pattern id="ds-building-far" width="17.639" height="17.639" patternUnits="userSpaceOnUse"><rect width="17.639" height="17.639" fill="url(#ds-building-far-tile)"/></pattern>
<pattern id="ds-tree-near-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-tree-near-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="17.778" height="21.167" mask-type="alpha"><rect width="17.778" height="21.167" fill="url(#ds-tree-near-paper)"/></mask>
<pattern id="ds-tree-near-sheet-1" width="5.926" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-0.583" y="0.128" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.512 1.319)"/>
<rect x="5.342" y="0.128" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.438 1.319)"/>
<rect x="-0.583" y="21.295" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.512 22.485)"/>
<rect x="5.342" y="21.295" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.438 22.485)"/>
<rect x="2.231" y="0.444" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.327 1.634)"/>
<rect x="-2.704" y="-0.747" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -1.608 0.444)"/>
<rect x="3.222" y="-0.747" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.317 0.444)"/>
<rect x="-2.704" y="20.42" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -1.608 21.61)"/>
<rect x="3.222" y="20.42" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.317 21.61)"/>
<rect x="-0.804" y="1.167" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.291 2.358)"/>
<rect x="5.121" y="1.167" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.217 2.358)"/>
<rect x="2.33" y="0.984" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.425 2.175)"/>
<rect x="-2.021" y="1.145" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -0.926 2.336)"/>
<rect x="3.905" y="1.145" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 5 2.336)"/>
<rect x="-0.513" y="3.488" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.582 4.679)"/>
<rect x="5.413" y="3.488" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.508 4.679)"/>
<rect x="2.535" y="3.829" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.63 5.019)"/>
<rect x="2.884" y="3.189" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.979 4.379)"/>
<rect x="-0.805" y="6.259" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.29 7.449)"/>
<rect x="5.121" y="6.259" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.216 7.449)"/>
<rect x="2.48" y="6.133" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.575 7.324)"/>
<rect x="-1.438" y="6.015" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -0.343 7.206)"/>
<rect x="4.488" y="6.015" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 5.583 7.206)"/>
<rect x="0.78" y="8.034" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.875 9.224)"/>
<rect x="1.387" y="8.142" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.482 9.332)"/>
<rect x="-2.109" y="7.959" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -1.014 9.15)"/>
<rect x="3.817" y="7.959" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.912 9.15)"/>
<rect x="0.019" y="9.257" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.114 10.448)"/>
<rect x="5.945" y="9.257" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 7.04 10.448)"/>
<rect x="1.6" y="9.258" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.695 10.448)"/>
<rect x="-2.451" y="8.656" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -1.356 9.847)"/>
<rect x="3.475" y="8.656" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.57 9.847)"/>
<rect x="0.524" y="11.891" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.619 13.081)"/>
<rect x="2.827" y="11.684" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.922 12.875)"/>
<rect x="-1.976" y="11.795" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -0.881 12.986)"/>
<rect x="3.95" y="11.795" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 5.045 12.986)"/>
<rect x="-0.829" y="13.581" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.266 14.772)"/>
<rect x="5.097" y="13.581" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.192 14.772)"/>
<rect x="1.756" y="12.619" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.851 13.81)"/>
<rect x="-2.67" y="13.285" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -1.575 14.475)"/>
<rect x="3.256" y="13.285" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.351 14.475)"/>
<rect x="-0.595" y="15.087" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.5 16.278)"/>
<rect x="5.331" y="15.087" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.426 16.278)"/>
<rect x="2.076" y="14.965" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.171 16.155)"/>
<rect x="3.114" y="15.148" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.209 16.338)"/>
<rect x="-0.63" y="16.581" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.465 17.772)"/>
<rect x="5.296" y="16.581" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.391 17.772)"/>
<rect x="1.264" y="16.833" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.359 18.023)"/>
<rect x="3" y="17.381" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.095 18.571)"/>
<rect x="0.789" y="-2.365" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.884 -1.174)"/>
<rect x="0.789" y="18.802" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.884 19.992)"/>
<rect x="2.3" y="-1.32" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.395 -0.129)"/>
<rect x="2.3" y="19.847" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.395 21.038)"/>
<rect x="2.941" y="18.325" width="2.19" height="2.381" fill="#5c8944" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.036 19.515)"/>
</pattern>
<pattern id="ds-tree-near-sheet-2" width="17.778" height="7.056" patternUnits="userSpaceOnUse">
<rect x="-0.353" y="1.646" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="17.425" y="1.646" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="1.932" y="1.04" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="4.367" y="-0.035" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="4.367" y="7.02" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="9.228" y="-0.125" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="9.228" y="6.931" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="10.86" y="0.462" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="10.86" y="7.518" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="12.921" y="0.547" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="14.798" y="1.336" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="-0.701" y="2.285" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="17.077" y="2.285" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="1.662" y="2.362" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="5.186" y="3.856" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="7.653" y="2.002" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="9.886" y="4.067" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="11.93" y="3.193" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="15.267" y="3.289" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="-0.069" y="-1.343" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="17.709" y="-1.343" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="-0.069" y="5.712" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="17.709" y="5.712" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="2.875" y="-1.441" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="2.875" y="5.614" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="6.44" y="-1.602" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="6.44" y="5.454" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="7.051" y="4.238" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="11.633" y="5.236" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="12.262" y="-0.744" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="12.262" y="6.311" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="-1.998" y="-1.255" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="15.78" y="-1.255" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="-1.998" y="5.801" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="15.78" y="5.801" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
</pattern>
<pattern id="ds-tree-near-tile" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect width="17.778" height="21.167" fill="#183800" mask="url(#ds-tree-near-paper-mask)"/>
<rect width="17.778" height="21.167" fill="url(#ds-tree-near-sheet-1)"/>
<rect width="17.778" height="21.167" fill="url(#ds-tree-near-sheet-2)"/>
</pattern>
<pattern id="ds-tree-near" width="17.778" height="21.167" patternUnits="userSpaceOnUse"><rect width="17.778" height="21.167" fill="url(#ds-tree-near-tile)"/></pattern>
<pattern id="ds-tree-mid-sheet-0" width="1.764" height="5.292" patternUnits="userSpaceOnUse">
<rect x="-0.258" y="0.075" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.228 0.604)"/>
<rect x="1.506" y="0.075" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.992 0.604)"/>
<rect x="-0.258" y="5.367" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.228 5.896)"/>
<rect x="1.506" y="5.367" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.992 5.896)"/>
<rect x="-0.765" y="0.22" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -0.279 0.749)"/>
<rect x="0.999" y="0.22" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.485 0.749)"/>
<rect x="-0.323" y="0.556" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.164 1.085)"/>
<rect x="1.441" y="0.556" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.928 1.085)"/>
<rect x="0.525" y="0.551" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.012 1.081)"/>
<rect x="0.161" y="1.35" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.647 1.879)"/>
<rect x="1.925" y="1.35" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.411 1.879)"/>
<rect x="-0.9" y="1.423" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -0.413 1.953)"/>
<rect x="0.864" y="1.423" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.351 1.953)"/>
<rect x="-0.227" y="2.497" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.26 3.026)"/>
<rect x="1.537" y="2.497" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.024 3.026)"/>
<rect x="-0.63" y="2.653" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -0.143 3.182)"/>
<rect x="1.134" y="2.653" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.621 3.182)"/>
<rect x="-0.474" y="3.242" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.013 3.771)"/>
<rect x="1.29" y="3.242" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.777 3.771)"/>
<rect x="0.525" y="3.767" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.011 4.296)"/>
<rect x="0.227" y="-0.7" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.714 -0.171)"/>
<rect x="1.991" y="-0.7" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.478 -0.171)"/>
<rect x="0.227" y="4.591" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.714 5.121)"/>
<rect x="1.991" y="4.591" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.478 5.121)"/>
<rect x="-0.64" y="-0.754" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -0.153 -0.225)"/>
<rect x="1.124" y="-0.754" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.611 -0.225)"/>
<rect x="-0.64" y="4.537" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -0.153 5.067)"/>
<rect x="1.124" y="4.537" width="0.973" height="1.058" fill="#1b340e" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.611 5.067)"/>
</pattern>
<pattern id="ds-tree-mid-tile" width="5.292" height="5.292" patternUnits="userSpaceOnUse">
<rect width="5.292" height="5.292" fill="#657f57"/>
<rect width="5.292" height="5.292" fill="url(#ds-tree-mid-sheet-0)"/>
</pattern>
<pattern id="ds-tree-mid" width="5.292" height="5.292" patternUnits="userSpaceOnUse"><rect width="5.292" height="5.292" fill="url(#ds-tree-mid-tile)"/></pattern>
<pattern id="ds-tree-far-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-tree-far-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="17.778" height="21.167" mask-type="alpha"><rect width="17.778" height="21.167" fill="url(#ds-tree-far-paper)"/></mask>
<pattern id="ds-tree-far-tile" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect width="17.778" height="21.167" fill="#657f57"/>
<rect width="17.778" height="21.167" fill="#183800" mask="url(#ds-tree-far-paper-mask)"/>
</pattern>
<pattern id="ds-tree-far" width="17.778" height="21.167" patternUnits="userSpaceOnUse"><rect width="17.778" height="21.167" fill="url(#ds-tree-far-tile)"/></pattern>
<pattern id="ds-shrub-near-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-shrub-near-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="17.778" height="21.167" mask-type="alpha"><rect width="17.778" height="21.167" fill="url(#ds-shrub-near-paper)"/></mask>
<pattern id="ds-shrub-near-sheet-1" width="5.926" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-0.583" y="0.128" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.512 1.319)"/>
<rect x="5.342" y="0.128" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.438 1.319)"/>
<rect x="-0.583" y="21.295" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.512 22.485)"/>
<rect x="5.342" y="21.295" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.438 22.485)"/>
<rect x="2.231" y="0.444" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.327 1.634)"/>
<rect x="-2.704" y="-0.747" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -1.608 0.444)"/>
<rect x="3.222" y="-0.747" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.317 0.444)"/>
<rect x="-2.704" y="20.42" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -1.608 21.61)"/>
<rect x="3.222" y="20.42" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.317 21.61)"/>
<rect x="-0.804" y="1.167" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.291 2.358)"/>
<rect x="5.121" y="1.167" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.217 2.358)"/>
<rect x="2.33" y="0.984" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.425 2.175)"/>
<rect x="-2.021" y="1.145" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -0.926 2.336)"/>
<rect x="3.905" y="1.145" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 5 2.336)"/>
<rect x="-0.513" y="3.488" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.582 4.679)"/>
<rect x="5.413" y="3.488" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.508 4.679)"/>
<rect x="2.535" y="3.829" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.63 5.019)"/>
<rect x="2.884" y="3.189" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.979 4.379)"/>
<rect x="-0.805" y="6.259" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.29 7.449)"/>
<rect x="5.121" y="6.259" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.216 7.449)"/>
<rect x="2.48" y="6.133" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.575 7.324)"/>
<rect x="-1.438" y="6.015" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -0.343 7.206)"/>
<rect x="4.488" y="6.015" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 5.583 7.206)"/>
<rect x="0.78" y="8.034" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.875 9.224)"/>
<rect x="1.387" y="8.142" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.482 9.332)"/>
<rect x="-2.109" y="7.959" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -1.014 9.15)"/>
<rect x="3.817" y="7.959" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.912 9.15)"/>
<rect x="0.019" y="9.257" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.114 10.448)"/>
<rect x="5.945" y="9.257" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 7.04 10.448)"/>
<rect x="1.6" y="9.258" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.695 10.448)"/>
<rect x="-2.451" y="8.656" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -1.356 9.847)"/>
<rect x="3.475" y="8.656" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.57 9.847)"/>
<rect x="0.524" y="11.891" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.619 13.081)"/>
<rect x="2.827" y="11.684" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.922 12.875)"/>
<rect x="-1.976" y="11.795" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -0.881 12.986)"/>
<rect x="3.95" y="11.795" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 5.045 12.986)"/>
<rect x="-0.829" y="13.581" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.266 14.772)"/>
<rect x="5.097" y="13.581" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.192 14.772)"/>
<rect x="1.756" y="12.619" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.851 13.81)"/>
<rect x="-2.67" y="13.285" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 -1.575 14.475)"/>
<rect x="3.256" y="13.285" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.351 14.475)"/>
<rect x="-0.595" y="15.087" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.5 16.278)"/>
<rect x="5.331" y="15.087" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.426 16.278)"/>
<rect x="2.076" y="14.965" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.171 16.155)"/>
<rect x="3.114" y="15.148" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.209 16.338)"/>
<rect x="-0.63" y="16.581" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 0.465 17.772)"/>
<rect x="5.296" y="16.581" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 6.391 17.772)"/>
<rect x="1.264" y="16.833" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 2.359 18.023)"/>
<rect x="3" y="17.381" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.095 18.571)"/>
<rect x="0.789" y="-2.365" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.884 -1.174)"/>
<rect x="0.789" y="18.802" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 1.884 19.992)"/>
<rect x="2.3" y="-1.32" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.395 -0.129)"/>
<rect x="2.3" y="19.847" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 3.395 21.038)"/>
<rect x="2.941" y="18.325" width="2.19" height="2.381" fill="#267300" mask="url(#ds-1bb4640e-mask)" transform="rotate(-45 4.036 19.515)"/>
</pattern>
<pattern id="ds-shrub-near-sheet-2" width="17.778" height="7.056" patternUnits="userSpaceOnUse">
<rect x="-0.353" y="1.646" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="17.425" y="1.646" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="1.932" y="1.04" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="4.367" y="-0.035" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="4.367" y="7.02" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="9.228" y="-0.125" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="9.228" y="6.931" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="10.86" y="0.462" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="10.86" y="7.518" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="12.921" y="0.547" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="14.798" y="1.336" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="-0.701" y="2.285" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="17.077" y="2.285" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="1.662" y="2.362" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="5.186" y="3.856" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="7.653" y="2.002" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="9.886" y="4.067" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="11.93" y="3.193" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="15.267" y="3.289" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="-0.069" y="-1.343" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="17.709" y="-1.343" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="-0.069" y="5.712" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="17.709" y="5.712" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="2.875" y="-1.441" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="2.875" y="5.614" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="6.44" y="-1.602" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="6.44" y="5.454" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="7.051" y="4.238" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="11.633" y="5.236" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="12.262" y="-0.744" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="12.262" y="6.311" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="-1.998" y="-1.255" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="15.78" y="-1.255" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="-1.998" y="5.801" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
<rect x="15.78" y="5.801" width="1.857" height="1.235" fill="#abcd66" mask="url(#ds-f08c1e65-mask)"/>
</pattern>
<pattern id="ds-shrub-near-tile" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect width="17.778" height="21.167" fill="#183800" mask="url(#ds-shrub-near-paper-mask)"/>
<rect width="17.778" height="21.167" fill="url(#ds-shrub-near-sheet-1)"/>
<rect width="17.778" height="21.167" fill="url(#ds-shrub-near-sheet-2)"/>
</pattern>
<pattern id="ds-shrub-near" width="17.778" height="21.167" patternUnits="userSpaceOnUse"><rect width="17.778" height="21.167" fill="url(#ds-shrub-near-tile)"/></pattern>
<pattern id="ds-shrub-mid-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-shrub-mid-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="17.778" height="21.167" mask-type="alpha"><rect width="17.778" height="21.167" fill="url(#ds-shrub-mid-paper)"/></mask>
<pattern id="ds-shrub-mid-tile" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect width="17.778" height="21.167" fill="#183800" mask="url(#ds-shrub-mid-paper-mask)"/>
</pattern>
<pattern id="ds-shrub-mid" width="17.778" height="21.167" patternUnits="userSpaceOnUse"><rect width="17.778" height="21.167" fill="url(#ds-shrub-mid-tile)"/></pattern>
<pattern id="ds-shrub-far-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-shrub-far-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="17.778" height="21.167" mask-type="alpha"><rect width="17.778" height="21.167" fill="url(#ds-shrub-far-paper)"/></mask>
<pattern id="ds-shrub-far-tile" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect width="17.778" height="21.167" fill="#183800" mask="url(#ds-shrub-far-paper-mask)"/>
</pattern>
<pattern id="ds-shrub-far" width="17.778" height="21.167" patternUnits="userSpaceOnUse"><rect width="17.778" height="21.167" fill="url(#ds-shrub-far-tile)"/></pattern>
<pattern id="ds-grass-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-grass-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="17.778" height="21.167" mask-type="alpha"><rect width="17.778" height="21.167" fill="url(#ds-grass-paper)"/></mask>
<pattern id="ds-grass-sheet-1" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-3.011" y="4.591" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 0.535 6.707)"/>
<rect x="14.767" y="4.591" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 18.313 6.707)"/>
<rect x="3.268" y="3.1" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 6.815 5.217)"/>
<rect x="-4.487" y="3.155" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -0.941 5.271)"/>
<rect x="13.291" y="3.155" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 16.837 5.271)"/>
<rect x="-1.757" y="7.42" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 1.789 9.536)"/>
<rect x="16.021" y="7.42" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 19.567 9.536)"/>
<rect x="6.657" y="11.752" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.204 13.869)"/>
<rect x="-5.546" y="8.753" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -1.999 10.87)"/>
<rect x="12.232" y="8.753" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.779 10.87)"/>
<rect x="-1.248" y="14.857" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 2.299 16.974)"/>
<rect x="16.53" y="14.857" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 20.076 16.974)"/>
<rect x="6.641" y="-6.146" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 -4.029)"/>
<rect x="6.641" y="15.021" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 17.137)"/>
<rect x="-6.307" y="-4.721" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 -2.604)"/>
<rect x="11.471" y="-4.721" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 -2.604)"/>
<rect x="-6.307" y="16.446" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 18.563)"/>
<rect x="11.471" y="16.446" width="7.093" height="4.233" fill="#d7d79e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 18.563)"/>
</pattern>
<pattern id="ds-grass-sheet-2" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="1.212" y="3.033" width="2.92" height="3.175" fill="#9cc260" mask="url(#ds-1bb4640e-mask)"/>
<rect x="4.712" y="6.537" width="2.92" height="3.175" fill="#9cc260" mask="url(#ds-1bb4640e-mask)"/>
<rect x="-3.395" y="5.512" width="2.92" height="3.175" fill="#9cc260" mask="url(#ds-1bb4640e-mask)"/>
<rect x="14.383" y="5.512" width="2.92" height="3.175" fill="#9cc260" mask="url(#ds-1bb4640e-mask)"/>
<rect x="1.341" y="16.116" width="2.92" height="3.175" fill="#9cc260" mask="url(#ds-1bb4640e-mask)"/>
<rect x="9.695" y="16.32" width="2.92" height="3.175" fill="#9cc260" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="-2.674" width="2.92" height="3.175" fill="#9cc260" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="18.493" width="2.92" height="3.175" fill="#9cc260" mask="url(#ds-1bb4640e-mask)"/>
</pattern>
<pattern id="ds-grass-sheet-3" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-1.155" y="1.031" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 2.442)"/>
<rect x="16.623" y="1.031" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 2.442)"/>
<rect x="-1.155" y="22.197" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 23.608)"/>
<rect x="16.623" y="22.197" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 23.608)"/>
<rect x="0.839" y="8.26" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 2.961 9.671)"/>
<rect x="4.425" y="5.893" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.547 7.304)"/>
<rect x="6.901" y="2.648" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 9.024 4.059)"/>
<rect x="9.894" y="4.689" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 12.017 6.101)"/>
<rect x="12.56" y="5.591" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.682 7.002)"/>
<rect x="-2.531" y="3.239" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.408 4.65)"/>
<rect x="15.247" y="3.239" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.37 4.65)"/>
<rect x="-1.729" y="10.758" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.394 12.169)"/>
<rect x="16.049" y="10.758" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.172 12.169)"/>
<rect x="2.254" y="10.945" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 4.376 12.356)"/>
<rect x="4.619" y="15.742" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.742 17.153)"/>
<rect x="5.648" y="-3.694" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 -2.283)"/>
<rect x="5.648" y="17.473" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 18.884)"/>
<rect x="8.12" y="-2.82" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 -1.409)"/>
<rect x="8.12" y="18.347" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 19.758)"/>
<rect x="12.712" y="11.457" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.834 12.868)"/>
<rect x="-2.818" y="16.923" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.695 18.334)"/>
<rect x="14.96" y="16.923" width="4.245" height="2.822" fill="#b0cd67" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.083 18.334)"/>
</pattern>
<pattern id="ds-grass-sheet-4" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<image href="${ds_df4f3810}" x="1.731" y="0.756" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="6.383" y="3.648" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="14.749" y="2.701" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="2.75" y="5.637" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="9.734" y="6.453" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="15.954" y="6.814" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="4.446" y="10.106" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="6.317" y="8.88" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="15.61" y="8.955" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="3.352" y="15.107" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="5.751" y="15.8" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="11.52" y="16.149" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="4.457" y="17.627" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="9.702" y="19.813" width="1.054" height="0.441" preserveAspectRatio="none"/>
<image href="${ds_df4f3810}" x="12.065" y="19.549" width="1.054" height="0.441" preserveAspectRatio="none"/>
</pattern>
<pattern id="ds-grass-tile" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect width="17.778" height="21.167" fill="#c2e6ac"/>
<rect width="17.778" height="21.167" fill="#abcd66" mask="url(#ds-grass-paper-mask)"/>
<rect width="17.778" height="21.167" fill="url(#ds-grass-sheet-1)"/>
<rect width="17.778" height="21.167" fill="url(#ds-grass-sheet-2)"/>
<rect width="17.778" height="21.167" fill="url(#ds-grass-sheet-3)"/>
<rect width="17.778" height="21.167" fill="url(#ds-grass-sheet-4)"/>
</pattern>
<pattern id="ds-grass" width="17.778" height="21.167" patternUnits="userSpaceOnUse"><rect width="17.778" height="21.167" fill="url(#ds-grass-tile)"/></pattern>
<pattern id="ds-water-sheet-0" width="13.333" height="10.583" patternUnits="userSpaceOnUse">
<rect x="-1.032" y="1.682" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 1.257 3.27)"/>
<rect x="12.301" y="1.682" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 14.59 3.27)"/>
<rect x="3.856" y="-0.832" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 6.145 0.755)"/>
<rect x="3.856" y="9.751" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 6.145 11.338)"/>
<rect x="7.283" y="0.658" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 9.572 2.245)"/>
<rect x="7.283" y="11.241" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 9.572 12.829)"/>
<rect x="7.852" y="1.774" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 10.141 3.362)"/>
<rect x="-1.437" y="3.019" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 0.852 4.607)"/>
<rect x="11.897" y="3.019" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 14.186 4.607)"/>
<rect x="2.458" y="4.016" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 4.747 5.604)"/>
<rect x="4.792" y="4.363" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 7.081 5.95)"/>
<rect x="-2.848" y="3.748" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 -0.559 5.335)"/>
<rect x="10.485" y="3.748" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 12.774 5.335)"/>
<rect x="0.359" y="-2.91" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 2.648 -1.323)"/>
<rect x="13.693" y="-2.91" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 15.982 -1.323)"/>
<rect x="0.359" y="7.673" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 2.648 9.26)"/>
<rect x="13.693" y="7.673" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 15.982 9.26)"/>
<rect x="3.794" y="6.106" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 6.083 7.694)"/>
<rect x="5.573" y="-3.459" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 7.862 -1.872)"/>
<rect x="5.573" y="7.124" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 7.862 8.711)"/>
<rect x="8.058" y="-1.682" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 10.347 -0.095)"/>
<rect x="8.058" y="8.901" width="4.578" height="3.175" fill="#acccea" mask="url(#ds-0b0e781b-mask)" transform="rotate(-180 10.347 10.488)"/>
</pattern>
<pattern id="ds-water-sheet-1" width="8.889" height="10.583" patternUnits="userSpaceOnUse">
<rect x="-1.007" y="0.918" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 0.576 2.417)"/>
<rect x="7.882" y="0.918" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 9.464 2.417)"/>
<rect x="2.16" y="1.497" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 3.742 2.996)"/>
<rect x="3.275" y="-0.686" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 4.857 0.813)"/>
<rect x="3.275" y="9.897" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 4.857 11.397)"/>
<rect x="-3.478" y="-0.705" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 -1.895 0.794)"/>
<rect x="5.411" y="-0.705" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 6.994 0.794)"/>
<rect x="-3.478" y="9.878" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 -1.895 11.378)"/>
<rect x="5.411" y="9.878" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 6.994 11.378)"/>
<rect x="0.049" y="2.488" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 1.631 3.987)"/>
<rect x="8.937" y="2.488" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 10.52 3.987)"/>
<rect x="1.82" y="2.783" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 3.403 4.282)"/>
<rect x="3.517" y="3.551" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 5.099 5.05)"/>
<rect x="-1.943" y="4.175" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 -0.361 5.674)"/>
<rect x="6.946" y="4.175" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 8.528 5.674)"/>
<rect x="-1.551" y="6.529" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 0.032 8.029)"/>
<rect x="7.338" y="6.529" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 8.921 8.029)"/>
<rect x="0.966" y="-1.953" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 2.548 -0.454)"/>
<rect x="0.966" y="8.63" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 2.548 10.129)"/>
<rect x="4.661" y="-2.184" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 6.244 -0.684)"/>
<rect x="4.661" y="8.4" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 6.244 9.899)"/>
<rect x="-1.968" y="-2.4" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 -0.386 -0.9)"/>
<rect x="6.92" y="-2.4" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 8.503 -0.9)"/>
<rect x="-1.968" y="8.184" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 -0.386 9.683)"/>
<rect x="6.92" y="8.184" width="3.165" height="2.999" fill="#bfdded" mask="url(#ds-9c8ef47c-mask)" transform="rotate(-180 8.503 9.683)"/>
</pattern>
<pattern id="ds-water-paper" width="13.333" height="10.583" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="13.333" height="10.583" preserveAspectRatio="none"/></pattern>
<mask id="ds-water-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="26.667" height="21.167" mask-type="alpha"><rect width="26.667" height="21.167" fill="url(#ds-water-paper)"/></mask>
<pattern id="ds-water-tile" width="26.667" height="21.167" patternUnits="userSpaceOnUse">
<rect width="26.667" height="21.167" fill="#d7e4ff"/>
<rect width="26.667" height="21.167" fill="url(#ds-water-sheet-0)"/>
<rect width="26.667" height="21.167" fill="url(#ds-water-sheet-1)"/>
<rect width="26.667" height="21.167" fill="#d9f6ff" mask="url(#ds-water-paper-mask)"/>
</pattern>
<pattern id="ds-water" width="26.667" height="21.167" patternUnits="userSpaceOnUse"><rect width="26.667" height="21.167" fill="url(#ds-water-tile)"/></pattern>
<pattern id="ds-sand-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-sand-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="17.778" height="21.167" mask-type="alpha"><rect width="17.778" height="21.167" fill="url(#ds-sand-paper)"/></mask>
<pattern id="ds-sand-sheet-1" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-3.011" y="4.591" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 0.535 6.707)"/>
<rect x="14.767" y="4.591" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 18.313 6.707)"/>
<rect x="3.268" y="3.1" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 6.815 5.217)"/>
<rect x="-4.487" y="3.155" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -0.941 5.271)"/>
<rect x="13.291" y="3.155" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 16.837 5.271)"/>
<rect x="-1.757" y="7.42" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 1.789 9.536)"/>
<rect x="16.021" y="7.42" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 19.567 9.536)"/>
<rect x="6.657" y="11.752" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.204 13.869)"/>
<rect x="-5.546" y="8.753" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -1.999 10.87)"/>
<rect x="12.232" y="8.753" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.779 10.87)"/>
<rect x="-1.248" y="14.857" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 2.299 16.974)"/>
<rect x="16.53" y="14.857" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 20.076 16.974)"/>
<rect x="6.641" y="-6.146" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 -4.029)"/>
<rect x="6.641" y="15.021" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 17.137)"/>
<rect x="-6.307" y="-4.721" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 -2.604)"/>
<rect x="11.471" y="-4.721" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 -2.604)"/>
<rect x="-6.307" y="16.446" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 18.563)"/>
<rect x="11.471" y="16.446" width="7.093" height="4.233" fill="#f5ca7a" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 18.563)"/>
</pattern>
<pattern id="ds-sand-sheet-2" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="1.212" y="3.033" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="4.712" y="6.537" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="-3.395" y="5.512" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="14.383" y="5.512" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="1.341" y="16.116" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="9.695" y="16.32" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="-2.674" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="18.493" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
</pattern>
<pattern id="ds-sand-sheet-3" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-1.155" y="1.031" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 2.442)"/>
<rect x="16.623" y="1.031" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 2.442)"/>
<rect x="-1.155" y="22.197" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 23.608)"/>
<rect x="16.623" y="22.197" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 23.608)"/>
<rect x="0.839" y="8.26" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 2.961 9.671)"/>
<rect x="4.425" y="5.893" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.547 7.304)"/>
<rect x="6.901" y="2.648" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 9.024 4.059)"/>
<rect x="9.894" y="4.689" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 12.017 6.101)"/>
<rect x="12.56" y="5.591" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.682 7.002)"/>
<rect x="-2.531" y="3.239" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.408 4.65)"/>
<rect x="15.247" y="3.239" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.37 4.65)"/>
<rect x="-1.729" y="10.758" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.394 12.169)"/>
<rect x="16.049" y="10.758" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.172 12.169)"/>
<rect x="2.254" y="10.945" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 4.376 12.356)"/>
<rect x="4.619" y="15.742" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.742 17.153)"/>
<rect x="5.648" y="-3.694" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 -2.283)"/>
<rect x="5.648" y="17.473" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 18.884)"/>
<rect x="8.12" y="-2.82" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 -1.409)"/>
<rect x="8.12" y="18.347" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 19.758)"/>
<rect x="12.712" y="11.457" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.834 12.868)"/>
<rect x="-2.818" y="16.923" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.695 18.334)"/>
<rect x="14.96" y="16.923" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.083 18.334)"/>
</pattern>
<pattern id="ds-sand-sheet-4" width="17.778" height="4.233" patternUnits="userSpaceOnUse">
<circle cx="0.354" cy="2.901" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="2.303" cy="3.596" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="2.989" cy="0.976" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="4.304" cy="0.953" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="6.474" cy="0.551" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="7.564" cy="0.906" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="8.608" cy="1.827" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="10.718" cy="2.576" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="10.96" cy="1.168" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="12.508" cy="3.688" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="14.783" cy="3.412" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="16.173" cy="3.153" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="17.708" cy="3.36" r="0.044" fill="none" stroke="#000000" stroke-width="0.018"/>
</pattern>
<pattern id="ds-sand-sheet-5" width="8.889" height="21.167" patternUnits="userSpaceOnUse">
<circle cx="1.693" cy="0.698" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="5.182" cy="2.763" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="2.569" cy="5.111" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="6.902" cy="4.184" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="3.252" cy="7.791" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="7.916" cy="8.048" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="3.73" cy="10.4" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="5.134" cy="9.525" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="3.214" cy="12.602" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="7.354" cy="13.972" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="0.264" cy="17.491" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="4.591" cy="17.74" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="3.738" cy="18.796" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
<circle cx="7.672" cy="20.357" r="0.132" fill="none" stroke="#000000" stroke-width="0.013"/>
</pattern>
<pattern id="ds-sand-sheet-6" width="17.778" height="5.292" patternUnits="userSpaceOnUse">
<circle cx="0.496" cy="3.479" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="1.743" cy="0.755" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="2.103" cy="1.983" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="3.424" cy="4.288" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="4.905" cy="3.183" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="5.812" cy="3.499" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="6.426" cy="2.329" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="7.49" cy="4.794" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="8.428" cy="4.333" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="9.49" cy="3.635" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="10.81" cy="2.141" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="12.384" cy="0.098" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="12.613" cy="4.842" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="14.127" cy="0.481" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="15.673" cy="5.01" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="15.804" cy="2.239" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
<circle cx="16.873" cy="1.654" r="0.088" fill="none" stroke="#000000" stroke-width="0.018"/>
</pattern>
<pattern id="ds-sand-sheet-7" width="17.778" height="4.233" patternUnits="userSpaceOnUse">
<circle cx="4.221" cy="0.889" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="7.008" cy="1.057" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="13.002" cy="0.71" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="0.544" cy="1.86" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="6.823" cy="1.806" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="16.145" cy="1.869" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="2.616" cy="3.033" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="11.78" cy="2.239" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="14.915" cy="3.131" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="4.38" cy="3.645" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="7.731" cy="-0.05" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="7.731" cy="4.184" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
<circle cx="12.356" cy="3.98" r="0.088" fill="none" stroke="#000000" stroke-width="0.035"/>
</pattern>
<pattern id="ds-sand-tile" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect width="17.778" height="21.167" fill="#f4eba6"/>
<rect width="17.778" height="21.167" fill="#cdb559" mask="url(#ds-sand-paper-mask)"/>
<rect width="17.778" height="21.167" fill="url(#ds-sand-sheet-1)"/>
<rect width="17.778" height="21.167" fill="url(#ds-sand-sheet-2)"/>
<rect width="17.778" height="21.167" fill="url(#ds-sand-sheet-3)"/>
<rect width="17.778" height="21.167" fill="url(#ds-sand-sheet-4)"/>
<rect width="17.778" height="21.167" fill="url(#ds-sand-sheet-5)"/>
<rect width="17.778" height="21.167" fill="url(#ds-sand-sheet-6)"/>
<rect width="17.778" height="21.167" fill="url(#ds-sand-sheet-7)"/>
</pattern>
<pattern id="ds-sand" width="17.778" height="21.167" patternUnits="userSpaceOnUse"><rect width="17.778" height="21.167" fill="url(#ds-sand-tile)"/></pattern>
<pattern id="ds-brick-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-brick-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="17.778" height="21.167" mask-type="alpha"><rect width="17.778" height="21.167" fill="url(#ds-brick-paper)"/></mask>
<pattern id="ds-brick-sheet-3" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-3.011" y="4.591" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 0.535 6.707)"/>
<rect x="14.767" y="4.591" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 18.313 6.707)"/>
<rect x="3.268" y="3.1" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 6.815 5.217)"/>
<rect x="-4.487" y="3.155" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -0.941 5.271)"/>
<rect x="13.291" y="3.155" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 16.837 5.271)"/>
<rect x="-1.757" y="7.42" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 1.789 9.536)"/>
<rect x="16.021" y="7.42" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 19.567 9.536)"/>
<rect x="6.657" y="11.752" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.204 13.869)"/>
<rect x="-5.546" y="8.753" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -1.999 10.87)"/>
<rect x="12.232" y="8.753" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.779 10.87)"/>
<rect x="-1.248" y="14.857" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 2.299 16.974)"/>
<rect x="16.53" y="14.857" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 20.076 16.974)"/>
<rect x="6.641" y="-6.146" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 -4.029)"/>
<rect x="6.641" y="15.021" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 17.137)"/>
<rect x="-6.307" y="-4.721" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 -2.604)"/>
<rect x="11.471" y="-4.721" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 -2.604)"/>
<rect x="-6.307" y="16.446" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 18.563)"/>
<rect x="11.471" y="16.446" width="7.093" height="4.233" fill="#cccccc" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 18.563)"/>
</pattern>
<pattern id="ds-brick-sheet-4" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="1.212" y="3.033" width="2.92" height="3.175" fill="#d4d4d4" mask="url(#ds-1bb4640e-mask)"/>
<rect x="4.712" y="6.537" width="2.92" height="3.175" fill="#d4d4d4" mask="url(#ds-1bb4640e-mask)"/>
<rect x="-3.395" y="5.512" width="2.92" height="3.175" fill="#d4d4d4" mask="url(#ds-1bb4640e-mask)"/>
<rect x="14.383" y="5.512" width="2.92" height="3.175" fill="#d4d4d4" mask="url(#ds-1bb4640e-mask)"/>
<rect x="1.341" y="16.116" width="2.92" height="3.175" fill="#d4d4d4" mask="url(#ds-1bb4640e-mask)"/>
<rect x="9.695" y="16.32" width="2.92" height="3.175" fill="#d4d4d4" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="-2.674" width="2.92" height="3.175" fill="#d4d4d4" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="18.493" width="2.92" height="3.175" fill="#d4d4d4" mask="url(#ds-1bb4640e-mask)"/>
</pattern>
<pattern id="ds-brick-sheet-5" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-1.155" y="1.031" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 2.442)"/>
<rect x="16.623" y="1.031" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 2.442)"/>
<rect x="-1.155" y="22.197" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 23.608)"/>
<rect x="16.623" y="22.197" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 23.608)"/>
<rect x="0.839" y="8.26" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 2.961 9.671)"/>
<rect x="4.425" y="5.893" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.547 7.304)"/>
<rect x="6.901" y="2.648" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 9.024 4.059)"/>
<rect x="9.894" y="4.689" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 12.017 6.101)"/>
<rect x="12.56" y="5.591" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.682 7.002)"/>
<rect x="-2.531" y="3.239" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.408 4.65)"/>
<rect x="15.247" y="3.239" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.37 4.65)"/>
<rect x="-1.729" y="10.758" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.394 12.169)"/>
<rect x="16.049" y="10.758" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.172 12.169)"/>
<rect x="2.254" y="10.945" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 4.376 12.356)"/>
<rect x="4.619" y="15.742" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.742 17.153)"/>
<rect x="5.648" y="-3.694" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 -2.283)"/>
<rect x="5.648" y="17.473" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 18.884)"/>
<rect x="8.12" y="-2.82" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 -1.409)"/>
<rect x="8.12" y="18.347" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 19.758)"/>
<rect x="12.712" y="11.457" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.834 12.868)"/>
<rect x="-2.818" y="16.923" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.695 18.334)"/>
<rect x="14.96" y="16.923" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.083 18.334)"/>
</pattern>
<pattern id="ds-brick-tile" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect width="17.778" height="21.167" fill="#e1e1e1"/>
<path d="M0 0V21.167 M0.889 0V21.167 M1.778 0V21.167 M2.667 0V21.167 M3.556 0V21.167 M4.444 0V21.167 M5.333 0V21.167 M6.222 0V21.167 M7.111 0V21.167 M8 0V21.167 M8.889 0V21.167 M9.778 0V21.167 M10.667 0V21.167 M11.556 0V21.167 M12.444 0V21.167 M13.333 0V21.167 M14.222 0V21.167 M15.111 0V21.167 M16 0V21.167 M16.889 0V21.167 M17.778 0V21.167" fill="none" stroke="#000000" stroke-width="0.032"/>
<path d="M0 0.441H17.778 M0 1.323H17.778 M0 2.205H17.778 M0 3.087H17.778 M0 3.969H17.778 M0 4.851H17.778 M0 5.733H17.778 M0 6.615H17.778 M0 7.497H17.778 M0 8.378H17.778 M0 9.26H17.778 M0 10.142H17.778 M0 11.024H17.778 M0 11.906H17.778 M0 12.788H17.778 M0 13.67H17.778 M0 14.552H17.778 M0 15.434H17.778 M0 16.316H17.778 M0 17.198H17.778 M0 18.08H17.778 M0 18.962H17.778 M0 19.844H17.778 M0 20.726H17.778" fill="none" stroke="#000000" stroke-width="0.064"/>
<rect width="17.778" height="21.167" fill="#e1e1e1" mask="url(#ds-brick-paper-mask)"/>
<rect width="17.778" height="21.167" fill="url(#ds-brick-sheet-3)"/>
<rect width="17.778" height="21.167" fill="url(#ds-brick-sheet-4)"/>
<rect width="17.778" height="21.167" fill="url(#ds-brick-sheet-5)"/>
</pattern>
<pattern id="ds-brick" width="17.778" height="21.167" patternUnits="userSpaceOnUse"><rect width="17.778" height="21.167" fill="url(#ds-brick-tile)"/></pattern>
<pattern id="ds-grey-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-grey-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="17.778" height="21.167" mask-type="alpha"><rect width="17.778" height="21.167" fill="url(#ds-grey-paper)"/></mask>
<pattern id="ds-grey-sheet-1" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-3.011" y="4.591" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 0.535 6.707)"/>
<rect x="14.767" y="4.591" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 18.313 6.707)"/>
<rect x="3.268" y="3.1" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 6.815 5.217)"/>
<rect x="-4.487" y="3.155" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -0.941 5.271)"/>
<rect x="13.291" y="3.155" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 16.837 5.271)"/>
<rect x="-1.757" y="7.42" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 1.789 9.536)"/>
<rect x="16.021" y="7.42" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 19.567 9.536)"/>
<rect x="6.657" y="11.752" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.204 13.869)"/>
<rect x="-5.546" y="8.753" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -1.999 10.87)"/>
<rect x="12.232" y="8.753" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.779 10.87)"/>
<rect x="-1.248" y="14.857" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 2.299 16.974)"/>
<rect x="16.53" y="14.857" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 20.076 16.974)"/>
<rect x="6.641" y="-6.146" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 -4.029)"/>
<rect x="6.641" y="15.021" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 17.137)"/>
<rect x="-6.307" y="-4.721" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 -2.604)"/>
<rect x="11.471" y="-4.721" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 -2.604)"/>
<rect x="-6.307" y="16.446" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 18.563)"/>
<rect x="11.471" y="16.446" width="7.093" height="4.233" fill="#b2b2b2" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 18.563)"/>
</pattern>
<pattern id="ds-grey-sheet-2" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="1.212" y="3.033" width="2.92" height="3.175" fill="#cccccc" mask="url(#ds-1bb4640e-mask)"/>
<rect x="4.712" y="6.537" width="2.92" height="3.175" fill="#cccccc" mask="url(#ds-1bb4640e-mask)"/>
<rect x="-3.395" y="5.512" width="2.92" height="3.175" fill="#cccccc" mask="url(#ds-1bb4640e-mask)"/>
<rect x="14.383" y="5.512" width="2.92" height="3.175" fill="#cccccc" mask="url(#ds-1bb4640e-mask)"/>
<rect x="1.341" y="16.116" width="2.92" height="3.175" fill="#cccccc" mask="url(#ds-1bb4640e-mask)"/>
<rect x="9.695" y="16.32" width="2.92" height="3.175" fill="#cccccc" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="-2.674" width="2.92" height="3.175" fill="#cccccc" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="18.493" width="2.92" height="3.175" fill="#cccccc" mask="url(#ds-1bb4640e-mask)"/>
</pattern>
<pattern id="ds-grey-sheet-3" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-1.155" y="1.031" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 2.442)"/>
<rect x="16.623" y="1.031" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 2.442)"/>
<rect x="-1.155" y="22.197" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 23.608)"/>
<rect x="16.623" y="22.197" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 23.608)"/>
<rect x="0.839" y="8.26" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 2.961 9.671)"/>
<rect x="4.425" y="5.893" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.547 7.304)"/>
<rect x="6.901" y="2.648" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 9.024 4.059)"/>
<rect x="9.894" y="4.689" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 12.017 6.101)"/>
<rect x="12.56" y="5.591" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.682 7.002)"/>
<rect x="-2.531" y="3.239" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.408 4.65)"/>
<rect x="15.247" y="3.239" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.37 4.65)"/>
<rect x="-1.729" y="10.758" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.394 12.169)"/>
<rect x="16.049" y="10.758" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.172 12.169)"/>
<rect x="2.254" y="10.945" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 4.376 12.356)"/>
<rect x="4.619" y="15.742" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.742 17.153)"/>
<rect x="5.648" y="-3.694" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 -2.283)"/>
<rect x="5.648" y="17.473" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 18.884)"/>
<rect x="8.12" y="-2.82" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 -1.409)"/>
<rect x="8.12" y="18.347" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 19.758)"/>
<rect x="12.712" y="11.457" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.834 12.868)"/>
<rect x="-2.818" y="16.923" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.695 18.334)"/>
<rect x="14.96" y="16.923" width="4.245" height="2.822" fill="#b2b2b2" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.083 18.334)"/>
</pattern>
<pattern id="ds-grey-tile" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect width="17.778" height="21.167" fill="#b2b2b2"/>
<rect width="17.778" height="21.167" fill="#e1e1e1" mask="url(#ds-grey-paper-mask)"/>
<rect width="17.778" height="21.167" fill="url(#ds-grey-sheet-1)"/>
<rect width="17.778" height="21.167" fill="url(#ds-grey-sheet-2)"/>
<rect width="17.778" height="21.167" fill="url(#ds-grey-sheet-3)"/>
</pattern>
<pattern id="ds-grey" width="17.778" height="21.167" patternUnits="userSpaceOnUse"><rect width="17.778" height="21.167" fill="url(#ds-grey-tile)"/></pattern>
<pattern id="ds-brown-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-brown-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="17.778" height="21.167" mask-type="alpha"><rect width="17.778" height="21.167" fill="url(#ds-brown-paper)"/></mask>
<pattern id="ds-brown-sheet-1" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-3.011" y="4.591" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 0.535 6.707)"/>
<rect x="14.767" y="4.591" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 18.313 6.707)"/>
<rect x="3.268" y="3.1" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 6.815 5.217)"/>
<rect x="-4.487" y="3.155" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -0.941 5.271)"/>
<rect x="13.291" y="3.155" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 16.837 5.271)"/>
<rect x="-1.757" y="7.42" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 1.789 9.536)"/>
<rect x="16.021" y="7.42" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 19.567 9.536)"/>
<rect x="6.657" y="11.752" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.204 13.869)"/>
<rect x="-5.546" y="8.753" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -1.999 10.87)"/>
<rect x="12.232" y="8.753" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.779 10.87)"/>
<rect x="-1.248" y="14.857" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 2.299 16.974)"/>
<rect x="16.53" y="14.857" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 20.076 16.974)"/>
<rect x="6.641" y="-6.146" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 -4.029)"/>
<rect x="6.641" y="15.021" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 17.137)"/>
<rect x="-6.307" y="-4.721" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 -2.604)"/>
<rect x="11.471" y="-4.721" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 -2.604)"/>
<rect x="-6.307" y="16.446" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 18.563)"/>
<rect x="11.471" y="16.446" width="7.093" height="4.233" fill="#d7b09e" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 18.563)"/>
</pattern>
<pattern id="ds-brown-sheet-2" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="1.212" y="3.033" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="4.712" y="6.537" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="-3.395" y="5.512" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="14.383" y="5.512" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="1.341" y="16.116" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="9.695" y="16.32" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="-2.674" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="18.493" width="2.92" height="3.175" fill="#ffebaf" mask="url(#ds-1bb4640e-mask)"/>
</pattern>
<pattern id="ds-brown-sheet-3" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-1.155" y="1.031" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 2.442)"/>
<rect x="16.623" y="1.031" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 2.442)"/>
<rect x="-1.155" y="22.197" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 23.608)"/>
<rect x="16.623" y="22.197" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 23.608)"/>
<rect x="0.839" y="8.26" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 2.961 9.671)"/>
<rect x="4.425" y="5.893" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.547 7.304)"/>
<rect x="6.901" y="2.648" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 9.024 4.059)"/>
<rect x="9.894" y="4.689" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 12.017 6.101)"/>
<rect x="12.56" y="5.591" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.682 7.002)"/>
<rect x="-2.531" y="3.239" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.408 4.65)"/>
<rect x="15.247" y="3.239" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.37 4.65)"/>
<rect x="-1.729" y="10.758" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.394 12.169)"/>
<rect x="16.049" y="10.758" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.172 12.169)"/>
<rect x="2.254" y="10.945" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 4.376 12.356)"/>
<rect x="4.619" y="15.742" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.742 17.153)"/>
<rect x="5.648" y="-3.694" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 -2.283)"/>
<rect x="5.648" y="17.473" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 18.884)"/>
<rect x="8.12" y="-2.82" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 -1.409)"/>
<rect x="8.12" y="18.347" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 19.758)"/>
<rect x="12.712" y="11.457" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.834 12.868)"/>
<rect x="-2.818" y="16.923" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.695 18.334)"/>
<rect x="14.96" y="16.923" width="4.245" height="2.822" fill="#d7c29e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.083 18.334)"/>
</pattern>
<pattern id="ds-brown-tile" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect width="17.778" height="21.167" fill="#e6e1c1"/>
<rect width="17.778" height="21.167" fill="#cdaa66" mask="url(#ds-brown-paper-mask)"/>
<rect width="17.778" height="21.167" fill="url(#ds-brown-sheet-1)"/>
<rect width="17.778" height="21.167" fill="url(#ds-brown-sheet-2)"/>
<rect width="17.778" height="21.167" fill="url(#ds-brown-sheet-3)"/>
</pattern>
<pattern id="ds-brown" width="17.778" height="21.167" patternUnits="userSpaceOnUse"><rect width="17.778" height="21.167" fill="url(#ds-brown-tile)"/></pattern>
<pattern id="ds-green-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-green-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="17.778" height="21.167" mask-type="alpha"><rect width="17.778" height="21.167" fill="url(#ds-green-paper)"/></mask>
<pattern id="ds-green-sheet-1" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-3.011" y="4.591" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 0.535 6.707)"/>
<rect x="14.767" y="4.591" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 18.313 6.707)"/>
<rect x="3.268" y="3.1" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 6.815 5.217)"/>
<rect x="-4.487" y="3.155" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -0.941 5.271)"/>
<rect x="13.291" y="3.155" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 16.837 5.271)"/>
<rect x="-1.757" y="7.42" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 1.789 9.536)"/>
<rect x="16.021" y="7.42" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 19.567 9.536)"/>
<rect x="6.657" y="11.752" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.204 13.869)"/>
<rect x="-5.546" y="8.753" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -1.999 10.87)"/>
<rect x="12.232" y="8.753" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.779 10.87)"/>
<rect x="-1.248" y="14.857" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 2.299 16.974)"/>
<rect x="16.53" y="14.857" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 20.076 16.974)"/>
<rect x="6.641" y="-6.146" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 -4.029)"/>
<rect x="6.641" y="15.021" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 10.187 17.137)"/>
<rect x="-6.307" y="-4.721" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 -2.604)"/>
<rect x="11.471" y="-4.721" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 -2.604)"/>
<rect x="-6.307" y="16.446" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 -2.76 18.563)"/>
<rect x="11.471" y="16.446" width="7.093" height="4.233" fill="#abcd66" mask="url(#ds-1f0fe8f5-mask)" transform="rotate(-90 15.017 18.563)"/>
</pattern>
<pattern id="ds-green-sheet-2" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="1.212" y="3.033" width="2.92" height="3.175" fill="#728944" mask="url(#ds-1bb4640e-mask)"/>
<rect x="4.712" y="6.537" width="2.92" height="3.175" fill="#728944" mask="url(#ds-1bb4640e-mask)"/>
<rect x="-3.395" y="5.512" width="2.92" height="3.175" fill="#728944" mask="url(#ds-1bb4640e-mask)"/>
<rect x="14.383" y="5.512" width="2.92" height="3.175" fill="#728944" mask="url(#ds-1bb4640e-mask)"/>
<rect x="1.341" y="16.116" width="2.92" height="3.175" fill="#728944" mask="url(#ds-1bb4640e-mask)"/>
<rect x="9.695" y="16.32" width="2.92" height="3.175" fill="#728944" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="-2.674" width="2.92" height="3.175" fill="#728944" mask="url(#ds-1bb4640e-mask)"/>
<rect x="12.44" y="18.493" width="2.92" height="3.175" fill="#728944" mask="url(#ds-1bb4640e-mask)"/>
</pattern>
<pattern id="ds-green-sheet-3" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect x="-1.155" y="1.031" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 2.442)"/>
<rect x="16.623" y="1.031" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 2.442)"/>
<rect x="-1.155" y="22.197" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.968 23.608)"/>
<rect x="16.623" y="22.197" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.745 23.608)"/>
<rect x="0.839" y="8.26" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 2.961 9.671)"/>
<rect x="4.425" y="5.893" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.547 7.304)"/>
<rect x="6.901" y="2.648" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 9.024 4.059)"/>
<rect x="9.894" y="4.689" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 12.017 6.101)"/>
<rect x="12.56" y="5.591" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.682 7.002)"/>
<rect x="-2.531" y="3.239" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.408 4.65)"/>
<rect x="15.247" y="3.239" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.37 4.65)"/>
<rect x="-1.729" y="10.758" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 0.394 12.169)"/>
<rect x="16.049" y="10.758" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 18.172 12.169)"/>
<rect x="2.254" y="10.945" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 4.376 12.356)"/>
<rect x="4.619" y="15.742" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 6.742 17.153)"/>
<rect x="5.648" y="-3.694" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 -2.283)"/>
<rect x="5.648" y="17.473" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 7.77 18.884)"/>
<rect x="8.12" y="-2.82" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 -1.409)"/>
<rect x="8.12" y="18.347" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 10.243 19.758)"/>
<rect x="12.712" y="11.457" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 14.834 12.868)"/>
<rect x="-2.818" y="16.923" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 -0.695 18.334)"/>
<rect x="14.96" y="16.923" width="4.245" height="2.822" fill="#b4d79e" mask="url(#ds-f08c1e65-mask)" transform="rotate(-45 17.083 18.334)"/>
</pattern>
<pattern id="ds-green-tile" width="17.778" height="21.167" patternUnits="userSpaceOnUse">
<rect width="17.778" height="21.167" fill="#95b77f"/>
<rect width="17.778" height="21.167" fill="#728944" mask="url(#ds-green-paper-mask)"/>
<rect width="17.778" height="21.167" fill="url(#ds-green-sheet-1)"/>
<rect width="17.778" height="21.167" fill="url(#ds-green-sheet-2)"/>
<rect width="17.778" height="21.167" fill="url(#ds-green-sheet-3)"/>
</pattern>
<pattern id="ds-green" width="17.778" height="21.167" patternUnits="userSpaceOnUse"><rect width="17.778" height="21.167" fill="url(#ds-green-tile)"/></pattern>
<pattern id="ds-paper-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><image href="${ds_6c7f0598}" width="8.889" height="7.056" preserveAspectRatio="none"/></pattern>
<mask id="ds-paper-paper-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="8.889" height="7.056" mask-type="alpha"><rect width="8.889" height="7.056" fill="url(#ds-paper-paper)"/></mask>
<pattern id="ds-paper-tile" width="8.889" height="7.056" patternUnits="userSpaceOnUse">
<rect width="8.889" height="7.056" fill="#e1e1e1" mask="url(#ds-paper-paper-mask)"/>
</pattern>
<pattern id="ds-paper" width="8.889" height="7.056" patternUnits="userSpaceOnUse"><rect width="8.889" height="7.056" fill="url(#ds-paper-tile)"/></pattern>
`;
