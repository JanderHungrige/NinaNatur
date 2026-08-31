/**
 * The textures a garden plan is drawn with.
 *
 * One definition per symbol, referenced by every object of a kind that uses it
 * — a pattern per object would be a defs block that grows with the garden.
 *
 * Everything here is measured in metres, because that is the canvas's unit. A
 * slab pattern sized in pixels would be a different slab at every zoom level,
 * which is the same mistake the drawing tolerances avoid. Colours come from CSS
 * so the plan follows the light and dark palettes rather than fixing its own.
 */

/** One patch of colour with a soft, uneven edge — the watercolour idea. */
function Wash({ id, className }: { id: string; className: string }) {
  return (
    <pattern id={id} width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="4" className={className} />
    </pattern>
  );
}

export function GardenSymbols() {
  return (
    <>
      {/*
        The hand-drawn edge. Turbulence displaced by a fraction of a metre
        gives an outline that wobbles like a pen rather than a plotter. The
        scale is in metres like everything else, so it stays proportionate
        when the user zooms.
      */}
      {/*
        The hand-drawn edge, the pigment, and the rim where the paint stops.

        Rebuilt in Wave 15 after the first attempt was merged unseen and the
        user said it still looked like CAD. Rasterising the plan with
        `qlmanage` and actually looking named three things at once: the wobble
        was too small to see, the "pigment" was desaturated noise multiplied
        in, which is grey dirt rather than paint, and the outline was a uniform
        hard stroke.

        Two wavelengths now: a long one bends the whole outline, a short one
        roughens it. One alone reads as either wavy or jittery. The pigment is
        a variation in the shape's *own* colour — black at low alpha through
        coarse turbulence — never a grey wash over the top.
      */}
      <filter id="watercolour" x="-20%" y="-20%" width="140%" height="140%"> <feTurbulence type="fractalNoise" baseFrequency="0.05 0.07" numOctaves="3" seed="7" result="long" /> <feDisplacementMap in="SourceGraphic" in2="long" scale="1.1" xChannelSelector="R" yChannelSelector="G" result="bent" /> <feTurbulence type="fractalNoise" baseFrequency="0.45" numOctaves="2" seed="11" result="short" /> <feDisplacementMap in="bent" in2="short" scale="0.35" xChannelSelector="R" yChannelSelector="G" result="wobbled" /> <feTurbulence type="fractalNoise" baseFrequency="0.13" numOctaves="4" seed="3" result="pig" /> <feColorMatrix in="pig" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.42 0 0 0 -0.10" result="pigA" /> <feComposite in="pigA" in2="wobbled" operator="in" result="pigIn" /> <feFlood flood-color="#000" result="dark" /> <feComposite in="dark" in2="pigIn" operator="in" result="shade" /> <feMerge result="painted"> <feMergeNode in="wobbled" /> <feMergeNode in="shade" /> </feMerge> <feMorphology in="painted" operator="erode" radius="0.18" result="inner" /> <feComposite in="painted" in2="inner" operator="out" result="rim" /> <feColorMatrix in="rim" type="matrix" values="0.6 0 0 0 0 0 0.6 0 0 0 0 0 0.6 0 0 0 0 0 0.45 0" result="pooled" /> <feMerge> <feMergeNode in="painted" /> <feMergeNode in="pooled" /> </feMerge> </filter>

      {/* A roof, drawn as a roof. This was a flat wash on the grounds that a
          building should not pretend to be a plant — true, and it left a house
          as a beige rectangle among textured ground, which reads as a plan that
          has no symbols at all. Battens are what a plan has always drawn. */}
      {/* A roof as staggered tiles. Parallel battens across a whole roof read as corrugated iron — evenly spaced lines are a hatch, not a roof. */}
      <pattern id="symbol-building" width="2.4" height="2.0" patternUnits="userSpaceOnUse">
        <rect width="2.4" height="2.0" className="symbol__building"/>
        <g fill="none" className="symbol__building-line" strokeWidth="0.035">
        <rect x="-0.034" y="0.015" width="0.423" height="0.322" rx="0.03"/>
        <rect x="0.452" y="0.023" width="0.436" height="0.325" rx="0.03"/>
        <rect x="0.961" y="-0.021" width="0.375" height="0.315" rx="0.03"/>
        <rect x="1.449" y="-0.034" width="0.435" height="0.305" rx="0.03"/>
        <rect x="1.893" y="-0.037" width="0.451" height="0.341" rx="0.03"/>
        <rect x="0.278" y="0.409" width="0.377" height="0.312" rx="0.03"/>
        <rect x="0.72" y="0.369" width="0.448" height="0.315" rx="0.03"/>
        <rect x="1.165" y="0.425" width="0.384" height="0.355" rx="0.03"/>
        <rect x="1.675" y="0.404" width="0.401" height="0.323" rx="0.03"/>
        <rect x="2.129" y="0.363" width="0.441" height="0.305" rx="0.03"/>
        <rect x="0.028" y="0.777" width="0.449" height="0.352" rx="0.03"/>
        <rect x="0.505" y="0.821" width="0.419" height="0.341" rx="0.03"/>
        <rect x="0.922" y="0.798" width="0.438" height="0.302" rx="0.03"/>
        <rect x="1.482" y="0.831" width="0.406" height="0.314" rx="0.03"/>
        <rect x="1.915" y="0.791" width="0.451" height="0.316" rx="0.03"/>
        <rect x="0.193" y="1.167" width="0.43" height="0.359" rx="0.03"/>
        <rect x="0.72" y="1.199" width="0.417" height="0.342" rx="0.03"/>
        <rect x="1.172" y="1.209" width="0.417" height="0.333" rx="0.03"/>
        <rect x="1.648" y="1.174" width="0.401" height="0.355" rx="0.03"/>
        <rect x="2.145" y="1.208" width="0.398" height="0.295" rx="0.03"/>
        <rect x="-0.043" y="1.625" width="0.434" height="0.315" rx="0.03"/>
        <rect x="0.498" y="1.614" width="0.443" height="0.357" rx="0.03"/>
        <rect x="0.951" y="1.639" width="0.448" height="0.331" rx="0.03"/>
        <rect x="1.478" y="1.599" width="0.403" height="0.306" rx="0.03"/>
        <rect x="1.958" y="1.573" width="0.38" height="0.346" rx="0.03"/>
        </g>
        </pattern>

      {/* Nothing has said what this is yet, and it should look like it. An
          unnamed element used to be a flat grey — indistinguishable from a
          deliberate surface, so nobody knew there was a question outstanding. */}
      <pattern id="symbol-plain" width="0.9" height="0.9" patternUnits="userSpaceOnUse">
        <rect width="0.9" height="0.9" className="symbol__plain" />
        <circle cx="0.45" cy="0.45" r="0.07" className="symbol__plain-dot" />
      </pattern>

      <Wash id="symbol-planting" className="symbol__planting" />

      {/* Masonry: courses, not bricks. At garden scale a real bond is noise. */}
      <pattern id="symbol-masonry" width="0.8" height="0.4" patternUnits="userSpaceOnUse">
        <rect width="0.8" height="0.4" className="symbol__masonry" />
        <path d="M0 0.4 H0.8 M0.4 0 V0.4" className="symbol__masonry-line" />
      </pattern>

      {/* A fence is uprights. */}
      <pattern id="symbol-fence" width="0.5" height="1" patternUnits="userSpaceOnUse">
        <rect width="0.5" height="1" className="symbol__fence" />
        <path d="M0.25 0 V1" className="symbol__fence-post" />
      </pattern>

      {/* Slabs, for paving and paths. */}
      <pattern id="symbol-slabs" width="1" height="1" patternUnits="userSpaceOnUse">
        <rect width="1" height="1" className="symbol__slabs" />
        <rect x="0.05" y="0.05" width="0.9" height="0.9" className="symbol__slabs-stone" />
      </pattern>

      {/* Tarmac: a dark wash with the faint grain of a road surface. Coarser
          than gravel on purpose — the two sit next to each other on a plan and
          must not read as the same ground. */}
      <pattern id="symbol-tarmac" width="0.9" height="0.9" patternUnits="userSpaceOnUse">
        <rect width="0.9" height="0.9" className="symbol__tarmac" />
        <circle cx="0.22" cy="0.31" r="0.045" className="symbol__tarmac-grit" />
        <circle cx="0.63" cy="0.14" r="0.035" className="symbol__tarmac-grit" />
        <circle cx="0.71" cy="0.66" r="0.05" className="symbol__tarmac-grit" />
        <circle cx="0.35" cy="0.74" r="0.03" className="symbol__tarmac-grit" />
      </pattern>

      {/* Gravel: stipple. Irregular on purpose — evenly spaced dots read as a
          manufactured surface rather than as loose stone. */}
      {/* Gravel, scattered. Same reason as the grass: an even grid of dots is a manufactured surface, not loose stone. */}
      <pattern id="symbol-stipple" width="2.7" height="2.5" patternUnits="userSpaceOnUse">
        <rect width="2.7" height="2.5" className="symbol__stipple"/>
        <g className="symbol__stipple-grain">
        <circle cx="1.16" cy="0.943" r="0.031"/>
        <circle cx="2.137" cy="0.056" r="0.048"/>
        <circle cx="2.214" cy="0.236" r="0.05"/>
        <circle cx="1.532" cy="0.139" r="0.042"/>
        <circle cx="1.742" cy="1.134" r="0.058"/>
        <circle cx="0.42" cy="0.616" r="0.03"/>
        <circle cx="1.265" cy="2.276" r="0.052"/>
        <circle cx="1.914" cy="0.968" r="0.059"/>
        <circle cx="0.286" cy="0.745" r="0.055"/>
        <circle cx="1.796" cy="1.061" r="0.029"/>
        <circle cx="0.685" cy="0.548" r="0.038"/>
        <circle cx="1.999" cy="0.523" r="0.065"/>
        <circle cx="2.168" cy="0.173" r="0.042"/>
        <circle cx="1.23" cy="0.097" r="0.044"/>
        <circle cx="2.234" cy="0.311" r="0.052"/>
        <circle cx="0.333" cy="1.44" r="0.065"/>
        <circle cx="0.531" cy="0.06" r="0.029"/>
        <circle cx="1.346" cy="0.082" r="0.029"/>
        <circle cx="1.242" cy="2.269" r="0.044"/>
        <circle cx="1.003" cy="1.586" r="0.029"/>
        <circle cx="1.443" cy="0.458" r="0.052"/>
        <circle cx="2.359" cy="0.171" r="0.05"/>
        <circle cx="1.507" cy="0.401" r="0.037"/>
        <circle cx="2.448" cy="2.455" r="0.03"/>
        <circle cx="1.747" cy="2.341" r="0.036"/>
        <circle cx="1.519" cy="0.144" r="0.041"/>
        <circle cx="1.671" cy="1.468" r="0.06"/>
        <circle cx="0.25" cy="0.88" r="0.064"/>
        <circle cx="1.454" cy="1.132" r="0.043"/>
        <circle cx="2.426" cy="1.43" r="0.026"/>
        <circle cx="1.974" cy="0.835" r="0.045"/>
        <circle cx="0.556" cy="1.115" r="0.04"/>
        <circle cx="0.255" cy="1.563" r="0.03"/>
        <circle cx="1.938" cy="0.101" r="0.06"/>
        <circle cx="1.994" cy="1.244" r="0.057"/>
        <circle cx="0.641" cy="1.825" r="0.044"/>
        <circle cx="0.599" cy="2.373" r="0.043"/>
        <circle cx="0.943" cy="2.121" r="0.042"/>
        <circle cx="1.655" cy="0.454" r="0.063"/>
        <circle cx="0.667" cy="0.162" r="0.069"/>
        <circle cx="0.458" cy="2.331" r="0.069"/>
        <circle cx="1.508" cy="0.069" r="0.028"/>
        <circle cx="0.545" cy="0.981" r="0.053"/>
        <circle cx="2.379" cy="0.898" r="0.031"/>
        <circle cx="1.4" cy="0.372" r="0.029"/>
        <circle cx="1.385" cy="1.724" r="0.028"/>
        <circle cx="1.132" cy="1.743" r="0.059"/>
        <circle cx="0.967" cy="2.187" r="0.033"/>
        <circle cx="1.771" cy="1.908" r="0.065"/>
        <circle cx="1.237" cy="0.28" r="0.027"/>
        <circle cx="1.32" cy="0.459" r="0.053"/>
        <circle cx="0.244" cy="1.928" r="0.035"/>
        </g>
        </pattern>

      {/* Grass: short upward strokes over a wash. */}
      {/* Tufts scattered by hand, not a blade per tile. A tile small enough to hold one mark repeats into a lattice, and a lattice is the single most technical thing on a plan. */}
      <pattern id="symbol-grass" width="3.1" height="2.9" patternUnits="userSpaceOnUse">
        <rect width="3.1" height="2.9" className="symbol__grass"/>
        <path d="M1.794 2.127 l0.071 -0.263 M2.122 2.633 l-0.006 -0.125 M2.691 1.867 l-0.062 -0.282 M1.363 0.74 l0.012 -0.218 M0.087 0.657 l0.067 -0.17 M2.194 0.497 l-0.058 -0.263 M1.779 0.405 l0.059 -0.12 M0.636 0.653 l0.06 -0.297 M0.86 2.742 l0.028 -0.217 M0.623 2.685 l0.075 -0.244 M2.552 0.887 l-0.053 -0.185 M0.458 0.232 l0.016 -0.174 M0.059 1.948 l-0.03 -0.181 M2.342 1.396 l-0.003 -0.177 M2.023 0.21 l-0.076 -0.296 M2.149 2.416 l0.046 -0.123 M1.075 1.67 l-0.073 -0.122 M0.557 2.725 l0.041 -0.155 M2.653 2.688 l-0.023 -0.182 M1.519 2.222 l0.04 -0.139 M2.282 2.457 l0.071 -0.127 M0.305 1.004 l0.067 -0.23 M1.002 2.638 l-0.03 -0.218 M0.937 0.547 l-0.056 -0.134 M1.98 2.841 l-0.072 -0.149 M2.813 1.544 l-0.042 -0.193 M1.713 2.364 l-0.013 -0.202 M0.206 2.615 l-0.001 -0.126 M2.398 0.416 l0.072 -0.252 M1.815 2.256 l-0.01 -0.139 M0.468 2.415 l-0.007 -0.173 M2.848 2.436 l-0.007 -0.296 M1.417 2.093 l-0.033 -0.206 M1.181 0.46 l0.078 -0.188 M2.737 1.806 l-0.026 -0.21 M0.3 0.812 l0.059 -0.261 M1.062 2.251 l0.031 -0.259 M1.909 2.177 l0.033 -0.185 M0.836 1.41 l0.031 -0.259 M0.873 2.698 l0.013 -0.237 M0.082 1.582 l0.027 -0.165 M1.346 2.337 l0.048 -0.237 M1.024 1.853 l0.053 -0.253 M1.03 2.41 l0.03 -0.277 M2.783 2.728 l0.005 -0.213 M0.515 2.393 l-0.004 -0.289" className="symbol__grass-blade" strokeWidth="0.035" fill="none" strokeLinecap="round"/>
        </pattern>

      {/* Water: horizontal ripples, the way a plan has always drawn water. */}
      {/* Ripples that wander and sometimes break off, the way a pen loses pressure. Perfect rows of identical waves are the same lattice again. */}
      <pattern id="symbol-water" width="3.4" height="2.6" patternUnits="userSpaceOnUse">
        <rect width="3.4" height="2.6" className="symbol__water"/>
        <path d="M-0.2 -0.026 q0.2695 -0.058 0.539 0 q0.2695 0.058 0.539 0 q0.2695 -0.058 0.539 0 q0.2695 0.058 0.539 0 q0.2695 -0.058 0.539 0 q0.2695 0.058 0.539 0 q0.2695 -0.058 0.539 0 M-0.2 0.323 q0.2505 -0.094 0.501 0 q0.2505 0.094 0.501 0 q0.2505 -0.094 0.501 0 q0.2505 0.094 0.501 0 q0.2505 -0.094 0.501 0 q0.2505 0.094 0.501 0 q0.2505 -0.094 0.501 0 q0.2505 0.094 0.501 0 M-0.2 0.699 q0.263 -0.092 0.526 0 q0.263 0.092 0.526 0 q0.263 -0.092 0.526 0 q0.263 0.092 0.526 0 q0.263 -0.092 0.526 0 q0.263 0.092 0.526 0 q0.263 -0.092 0.526 0 q0.263 0.092 0.526 0 M-0.2 1.147 q0.365 -0.071 0.73 0 q0.365 0.071 0.73 0 q0.365 -0.071 0.73 0 M-0.2 1.516 q0.234 -0.114 0.468 0 q0.234 0.114 0.468 0 q0.234 -0.114 0.468 0 q0.234 0.114 0.468 0 q0.234 -0.114 0.468 0 q0.234 0.114 0.468 0 q0.234 -0.114 0.468 0 q0.234 0.114 0.468 0 q0.234 -0.114 0.468 0 M-0.2 1.87 q0.3495 -0.109 0.699 0 q0.3495 0.109 0.699 0 q0.3495 -0.109 0.699 0 q0.3495 0.109 0.699 0 q0.3495 -0.109 0.699 0 q0.3495 0.109 0.699 0 M-0.2 2.187 q0.3175 -0.098 0.635 0 q0.3175 0.098 0.635 0 q0.3175 -0.098 0.635 0 q0.3175 0.098 0.635 0 q0.3175 -0.098 0.635 0 q0.3175 0.098 0.635 0" className="symbol__water-line" strokeWidth="0.045"
        fill="none" strokeLinecap="round"/>
        </pattern>

      {/* A crown is foliage: overlapping blobs, not a disc. This is the one
          the reference drawing is most recognisable by. */}
      {/* Sized against the tree, not against the tile: a 6 m crown has to show
          a handful of blobs, so the tile is metres across. At the first
          attempt it was 1.1 m with 30 cm leaves, which at ordinary zoom is a
          two-pixel dot — the crowns read as flat discs, which is the one thing
          this feature exists to stop. */}
      <pattern id="symbol-crown" width="2.4" height="2.4" patternUnits="userSpaceOnUse">
        <rect width="2.4" height="2.4" className="symbol__crown" />
        <circle cx="0.7" cy="0.75" r="0.62" className="symbol__crown-leaf" />
        <circle cx="1.7" cy="1.2" r="0.55" className="symbol__crown-leaf" />
        <circle cx="1.0" cy="1.9" r="0.48" className="symbol__crown-leaf" />
        <circle cx="2.2" cy="2.2" r="0.4" className="symbol__crown-leaf" />
      </pattern>

      {/* A hedge is the same idea, tighter: it reads as a clipped mass. */}
      <pattern id="symbol-foliage" width="1" height="1" patternUnits="userSpaceOnUse">
        <rect width="1" height="1" className="symbol__foliage" />
        <circle cx="0.3" cy="0.32" r="0.3" className="symbol__foliage-leaf" />
        <circle cx="0.78" cy="0.72" r="0.26" className="symbol__foliage-leaf" />
      </pattern>
    </>
  );
}
