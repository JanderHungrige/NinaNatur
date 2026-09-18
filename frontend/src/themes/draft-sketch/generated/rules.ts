/**
 * Provenance: adapted from Draft Sketch
 *
 * Generated from Draft_Sketch.stylx (sha256 4ef38ef8…) by
 * `python -m scripts.stylx_to_theme`. Do not edit: regenerate (doc 97).
 *
 * What his symbols draw along a shape rather than inside it — ink, rims,
 * drop shadows, corners, centres — bottom first, in metres at 1:250. His
 * scanned strokes become solid ones carrying the same ink (doc 97).
 */
import type { Overlay } from '../overlays';

export const OVERLAYS: Readonly<Record<string, readonly Overlay[]>> = {
  "ds-building-near": [
    {
      "kind": "shadow",
      "colour": "#000000",
      "opacity": 0.1,
      "dx": 0.5292,
      "dy": -0.5292,
      "wave": {
        "amplitude": 0.1764,
        "period": 1.4111,
        "seed": 1
      }
    },
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.1545,
      "wave": null,
      "dashes": null
    },
    {
      "kind": "overshoot",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.074,
      "length": 0.3276
    },
    {
      "kind": "ticks",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.037,
      "length": 0.3276,
      "spacing": 0.3528,
      "inset": 0.0882,
      "angle": 45.0
    }
  ],
  "ds-building-mid": [
    {
      "kind": "shadow",
      "colour": "#000000",
      "opacity": 0.2,
      "dx": 0.2646,
      "dy": -0.2646,
      "wave": {
        "amplitude": 0.0882,
        "period": 1.0583,
        "seed": 1
      }
    },
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.1102,
      "wave": {
        "amplitude": 0.0882,
        "period": 0.8819,
        "seed": 1
      },
      "dashes": null
    }
  ],
  "ds-building-far": [
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.0441,
      "wave": {
        "amplitude": 0.0882,
        "period": 0.7937,
        "seed": 1
      },
      "dashes": null
    }
  ],
  "ds-tree-near": [
    {
      "kind": "shadow",
      "colour": "#000000",
      "opacity": 0.1,
      "dx": 0.5292,
      "dy": -0.5292,
      "wave": {
        "amplitude": 0.3528,
        "period": 1.3229,
        "seed": 1
      }
    },
    {
      "kind": "wash",
      "fill": "url(#ds-tree-near-ramp-0)"
    },
    {
      "kind": "wash",
      "fill": "url(#ds-tree-near)"
    },
    {
      "kind": "wash",
      "fill": "url(#ds-tree-near-ramp-1)"
    },
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.1545,
      "wave": {
        "amplitude": 0.3528,
        "period": 1.3229,
        "seed": 1
      },
      "dashes": null
    },
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.103,
      "wave": {
        "amplitude": 0.5292,
        "period": 2.1167,
        "seed": 15
      },
      "dashes": null
    },
    {
      "kind": "centre",
      "mask": "ds-67b90642-mask",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.4609,
      "height": 0.5292,
      "rotation": -45.0
    }
  ],
  "ds-tree-mid": [
    {
      "kind": "shadow",
      "colour": "#000000",
      "opacity": 0.1,
      "dx": 0.2646,
      "dy": -0.2646,
      "wave": {
        "amplitude": 0.3528,
        "period": 1.3229,
        "seed": 1
      }
    },
    {
      "kind": "wash",
      "fill": "url(#ds-tree-mid-ramp-0)"
    },
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.0882,
      "wave": {
        "amplitude": 0.0882,
        "period": 0.8819,
        "seed": 1
      },
      "dashes": null
    },
    {
      "kind": "centre",
      "mask": "ds-67b90642-mask",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.3073,
      "height": 0.3528,
      "rotation": -45.0
    }
  ],
  "ds-tree-far": [
    {
      "kind": "wash",
      "fill": "url(#ds-tree-far-ramp-0)"
    },
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.0882,
      "wave": {
        "amplitude": 0.0882,
        "period": 0.7056,
        "seed": 1
      },
      "dashes": null
    },
    {
      "kind": "centre",
      "mask": "ds-67b90642-mask",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.3073,
      "height": 0.3528,
      "rotation": -45.0
    }
  ],
  "ds-grass": [
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.103,
      "wave": {
        "amplitude": 0.0882,
        "period": 1.5875,
        "seed": 1
      },
      "dashes": null
    }
  ],
  "ds-water": [
    {
      "kind": "band",
      "colour": "#6699cd",
      "opacity": 0.243,
      "width": 1.5875,
      "inset": 0.2646,
      "wave": {
        "amplitude": 0.0882,
        "period": 1.7639,
        "seed": 1
      }
    },
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.103,
      "wave": {
        "amplitude": 0.1764,
        "period": 2.8222,
        "seed": 1
      },
      "dashes": null
    }
  ],
  "ds-sand": [
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.103,
      "wave": {
        "amplitude": 0.0882,
        "period": 1.5875,
        "seed": 1
      },
      "dashes": null
    }
  ],
  "ds-brick": [
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.103,
      "wave": {
        "amplitude": 0.0882,
        "period": 1.5875,
        "seed": 1
      },
      "dashes": null
    }
  ],
  "ds-grey": [
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.103,
      "wave": {
        "amplitude": 0.0882,
        "period": 1.5875,
        "seed": 1
      },
      "dashes": null
    }
  ],
  "ds-brown": [
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.103,
      "wave": {
        "amplitude": 0.0882,
        "period": 1.5875,
        "seed": 1
      },
      "dashes": null
    }
  ],
  "ds-green": [
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.103,
      "wave": {
        "amplitude": 0.0882,
        "period": 1.5875,
        "seed": 1
      },
      "dashes": null
    }
  ],
  "ds-dashed": [
    {
      "kind": "ink",
      "colour": "#000000",
      "opacity": 1.0,
      "width": 0.103,
      "wave": {
        "amplitude": 0.0882,
        "period": 2.1167,
        "seed": 1
      },
      "dashes": [
        0.441,
        0.441
      ]
    }
  ]
};
