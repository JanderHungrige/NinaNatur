import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { LivingBackground } from './LivingBackground';

/** jsdom has no matchMedia. Answering it is how the reduced-motion path is
 *  reachable at all from a test. */
function wantsLessMotion(reduce: boolean): void {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => ({
      matches: reduce && query.includes('prefers-reduced-motion'),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
      onchange: null,
    })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('LivingBackground', () => {
  it('is hidden from anything that reads the page', () => {
    // Decoration. A screen reader announcing a particle field would be reading
    // the wallpaper aloud.
    render(<LivingBackground />);
    expect(screen.getByTestId('living-background').getAttribute('aria-hidden')).toBe('true');
  });

  it('draws the field as layers, not as hundreds of nodes', () => {
    // Each layer carries its whole field of motes in one background image. A
    // node per particle would be a composited layer per particle.
    const { container } = render(<LivingBackground />);
    expect(container.querySelectorAll('.living__layer')).toHaveLength(3);
    expect(container.querySelectorAll('.living__bokeh').length).toBeLessThanOrEqual(8);
  });

  it('gives the layers different depths to move at', () => {
    // Identical speeds are a flat sheet of dots. The parallax is the depth.
    const { container } = render(<LivingBackground />);
    for (const depth of ['far', 'mid', 'near']) {
      expect(container.querySelector(`.living__layer--${depth}`)).not.toBeNull();
    }
  });

  it('lights the field from above and gives it a floor to rise from', () => {
    // Without the floor the motes merely exist; with it they are coming from
    // somewhere, which is what the reference picture is doing.
    const { container } = render(<LivingBackground />);
    expect(container.querySelector('.living__glow')).not.toBeNull();
    expect(container.querySelector('.living__floor')).not.toBeNull();
  });

  it('plays the film muted, looping and inline', () => {
    // Not decoration, any of the three: without `muted` and `playsinline` iOS
    // Safari refuses to autoplay at all, and a background that stops after one
    // pass is a background that goes blank.
    wantsLessMotion(false);
    render(<LivingBackground videoSrc="/meadow.mp4" />);

    const video = screen.getByTestId('living-video') as HTMLVideoElement;
    expect(video.muted).toBe(true);
    expect(video.hasAttribute('loop')).toBe(true);
    expect(video.hasAttribute('playsinline')).toBe(true);
    expect(video.getAttribute('src')).toBe('/meadow.mp4');
  });

  it('does not even fetch the film when less motion was asked for', () => {
    // Hiding it with CSS would still download three megabytes and decode them
    // for the one visitor who asked for the opposite.
    wantsLessMotion(true);
    render(<LivingBackground videoSrc="/meadow.mp4" />);

    expect(screen.queryByTestId('living-video')).toBeNull();
    expect(screen.getByTestId('living-background').querySelectorAll('.living__layer'))
      .toHaveLength(3);
  });

  it('keeps the mote field until the film is actually playing', () => {
    // A slow connection or a codec this browser dislikes should leave a moving
    // background, not a black rectangle where one was promised.
    wantsLessMotion(false);
    const { container } = render(<LivingBackground videoSrc="/meadow.mp4" />);
    expect(container.querySelector('.living__field')?.getAttribute('data-covered'))
      .toBe('false');

    fireEvent.playing(screen.getByTestId('living-video'));
    expect(container.querySelector('.living__field')?.getAttribute('data-covered'))
      .toBe('true');
  });

  it('falls back to the field when the film fails', () => {
    wantsLessMotion(false);
    const { container } = render(<LivingBackground videoSrc="/meadow.mp4" />);
    fireEvent.playing(screen.getByTestId('living-video'));
    fireEvent.error(screen.getByTestId('living-video'));

    expect(container.querySelector('.living__field')?.getAttribute('data-covered'))
      .toBe('false');
  });

  it('darkens the film, and only the film', () => {
    // The clip is a sunlit meadow and the front door's type is pale. No scrim
    // over the mote field, though: that one was built dark already.
    wantsLessMotion(false);
    const { container } = render(<LivingBackground videoSrc="/meadow.mp4" />);
    expect(container.querySelector('.living__scrim')).toBeNull();

    fireEvent.playing(screen.getByTestId('living-video'));
    expect(container.querySelector('.living__scrim')).not.toBeNull();
  });

  it('is still a mote field when no film was given', () => {
    // The component predates the video and every other page still uses it bare.
    wantsLessMotion(false);
    const { container } = render(<LivingBackground />);
    expect(screen.queryByTestId('living-video')).toBeNull();
    expect(container.querySelectorAll('.living__layer')).toHaveLength(3);
  });

  it('leaves the film alone when the browser is saving data', () => {
    // Three megabytes is nothing on a desk and a real amount on a train, and
    // the page has a background either way.
    wantsLessMotion(false);
    vi.stubGlobal('navigator', { ...navigator, connection: { saveData: true } });
    render(<LivingBackground videoSrc="/meadow.mp4" />);

    expect(screen.queryByTestId('living-video')).toBeNull();
    expect(screen.getByTestId('living-background').querySelectorAll('.living__layer'))
      .toHaveLength(3);
  });

  it('plays it for a browser that says nothing about data at all', () => {
    // Safari and Firefox have no `connection`. Absent is not "saving".
    wantsLessMotion(false);
    vi.stubGlobal('navigator', { ...navigator, connection: undefined });
    render(<LivingBackground videoSrc="/meadow.mp4" />);

    expect(screen.queryByTestId('living-video')).not.toBeNull();
  });
});
