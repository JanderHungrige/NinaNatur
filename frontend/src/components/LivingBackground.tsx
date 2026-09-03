import { useEffect, useRef, useState } from 'react';

import { prefersLessData, usePrefersReducedMotion } from '../usePrefersReducedMotion';

/**
 * The moving field behind the front door.
 *
 * Two versions of the same idea. The video is the one that was made for it;
 * the mote field is CSS, and it is what plays when the video must not or
 * cannot.
 *
 * The mote field carries its whole field per layer as repeated radial
 * gradients in a single background image, so the browser composites three
 * layers and animates one transform on each. A hundred animated nodes would be
 * a hundred composited layers, and a canvas would be a `requestAnimationFrame`
 * loop running until the tab is closed.
 *
 * The video is only *added* to that. It is loaded at all only when the visitor
 * has asked for neither less motion nor less data — hiding it with CSS would
 * still download three megabytes and decode them for somebody who asked for the
 * opposite — and the field stays underneath until the first frame is actually
 * playing, so a slow connection or a codec this browser dislikes leaves a
 * moving background rather than a black hole.
 *
 * Everything here is decoration: `aria-hidden`, behind the content, and
 * unreachable by the pointer.
 */
export function LivingBackground({ videoSrc }: { videoSrc?: string }) {
  const reduced = usePrefersReducedMotion();
  const [playing, setPlaying] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const wanted = videoSrc !== undefined && !reduced && !prefersLessData();

  useEffect(() => {
    if (!wanted) {
      setPlaying(false);
      return;
    }
    // A background nobody is looking at should not be decoded. Browsers do
    // throttle hidden tabs, but not consistently, and this is 50 seconds of
    // 720p going round for a page that is not on screen.
    const onVisibility = () => {
      const element = video.current;
      if (element === null) return;
      if (document.hidden) element.pause();
      else void element.play().catch(() => undefined);
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, [wanted]);

  return (
    <div className="living" aria-hidden="true" data-testid="living-background">
      {/* The field stays mounted under the video: it is what shows while the
          video loads, and what remains if it never does. */}
      <div className="living__field" data-covered={playing ? 'true' : 'false'}>
        {/* Light from above, which is what makes the motes read as lit rather
            than as dots painted on. */}
        <div className="living__glow" />
        <div className="living__layer living__layer--far" />
        <div className="living__layer living__layer--mid" />
        <div className="living__layer living__layer--near" />
        {/* The bright band along the bottom: the motes rise *from* somewhere. */}
        <div className="living__floor" />
        {/* A few large, soft ones in front. Too many and the text behind them
            stops being readable, which is the one thing a background must not
            do. */}
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} className={`living__bokeh living__bokeh--${i}`} />
        ))}
      </div>

      {wanted && (
        <video
          ref={video}
          className="living__video"
          data-testid="living-video"
          src={videoSrc}
          // `muted` and `playsinline` are not decoration: without either of
          // them iOS Safari refuses to autoplay at all, and the file has no
          // audio track to mute in the first place.
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          tabIndex={-1}
          onPlaying={() => setPlaying(true)}
          // A missing file or a codec this browser will not take leaves the
          // mote field running rather than a black rectangle.
          onError={() => setPlaying(false)}
        />
      )}
      {/* Over the video, never over nothing: the clip is bright, and the front
          door's text is pale on dark. */}
      {playing && <div className="living__scrim" />}
    </div>
  );
}
