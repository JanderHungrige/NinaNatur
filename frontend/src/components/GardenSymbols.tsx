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
      <filter id="watercolour" x="-15%" y="-15%" width="130%" height="130%">
        {/* The frequency is per metre. At 0.6 the wobble was finer than a
            pixel at ordinary zoom and averaged back into a straight line; a
            wave every six metres or so is what reads as a drawn edge. */}
        <feTurbulence type="fractalNoise" baseFrequency="0.16" numOctaves={2} seed={7} result="noise" />
        <feDisplacementMap
          in="SourceGraphic"
          in2="noise"
          scale={0.42}
          xChannelSelector="R"
          yChannelSelector="G"
          result="wobbled"
        />

        {/* Pigment, not paint. A wobbled edge around a perfectly flat fill is
            still a technical drawing — one colour per shape is what reads as
            CAD. Fine noise multiplied back in mottles every wash at once,
            which is what watercolour does and what no per-symbol work would
            have achieved. */}
        <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves={2} seed={3} result="grain" />
        <feColorMatrix in="grain" type="saturate" values="0" result="greyGrain" />
        <feComponentTransfer in="greyGrain" result="softGrain">
          {/* Kept faint. Past about a quarter it stops being paper and starts
              being dirt. */}
          <feFuncA type="linear" slope="0.22" intercept="0.78" />
        </feComponentTransfer>
        <feComposite in="softGrain" in2="wobbled" operator="in" result="grainInside" />
        <feBlend in="wobbled" in2="grainInside" mode="multiply" result="painted" />

        {/* The rim. Watercolour pools where it stops: darker at the edge,
            thinner in the middle. Eroding the shape and keeping the
            difference is that band, in metres like everything else. */}
        <feMorphology in="painted" operator="erode" radius="0.11" result="inner" />
        <feComposite in="painted" in2="inner" operator="out" result="rim" />
        <feColorMatrix
          in="rim"
          type="matrix"
          values="0.72 0 0 0 0
                  0 0.72 0 0 0
                  0 0 0.72 0 0
                  0 0 0 0.5 0"
          result="pooledRim"
        />
        <feMerge>
          <feMergeNode in="painted" />
          <feMergeNode in="pooledRim" />
        </feMerge>
      </filter>

      {/* A roof, drawn as a roof. This was a flat wash on the grounds that a
          building should not pretend to be a plant — true, and it left a house
          as a beige rectangle among textured ground, which reads as a plan that
          has no symbols at all. Battens are what a plan has always drawn. */}
      <pattern id="symbol-building" width="1.2" height="1.2" patternUnits="userSpaceOnUse">
        <rect width="1.2" height="1.2" className="symbol__building" />
        <path d="M0 0 L1.2 1.2 M-0.3 0.9 L0.3 1.5 M0.9 -0.3 L1.5 0.3"
              className="symbol__building-line" />
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

      {/* Gravel: stipple. Irregular on purpose — evenly spaced dots read as a
          manufactured surface rather than as loose stone. */}
      <pattern id="symbol-stipple" width="0.6" height="0.6" patternUnits="userSpaceOnUse">
        <rect width="0.6" height="0.6" className="symbol__stipple" />
        <circle cx="0.15" cy="0.2" r="0.05" className="symbol__stipple-grain" />
        <circle cx="0.42" cy="0.09" r="0.04" className="symbol__stipple-grain" />
        <circle cx="0.5" cy="0.44" r="0.055" className="symbol__stipple-grain" />
        <circle cx="0.22" cy="0.5" r="0.035" className="symbol__stipple-grain" />
      </pattern>

      {/* Grass: short upward strokes over a wash. */}
      <pattern id="symbol-grass" width="0.7" height="0.7" patternUnits="userSpaceOnUse">
        <rect width="0.7" height="0.7" className="symbol__grass" />
        <path
          d="M0.15 0.6 l0.05 -0.22 M0.35 0.68 l-0.04 -0.2 M0.55 0.55 l0.06 -0.24"
          className="symbol__grass-blade"
        />
      </pattern>

      {/* Water: horizontal ripples, the way a plan has always drawn water. */}
      <pattern id="symbol-water" width="1.2" height="0.6" patternUnits="userSpaceOnUse">
        <rect width="1.2" height="0.6" className="symbol__water" />
        <path
          d="M0 0.2 q0.3 -0.12 0.6 0 t0.6 0 M0 0.45 q0.3 -0.12 0.6 0 t0.6 0"
          className="symbol__water-ripple"
        />
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
