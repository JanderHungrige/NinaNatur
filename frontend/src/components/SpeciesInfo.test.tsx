import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { SpeciesInfoOut } from '../api/client';
import { SpeciesInfo } from './SpeciesInfo';

const ARTICLE = {
  title: 'Gemeine Schafgarbe',
  extract: 'Die Gemeine Schafgarbe ist eine Pflanzenart aus der Familie der Korbblütler.',
  thumbnail_url: 'https://upload.example/achillea.jpg',
  page_url: 'https://de.wikipedia.org/wiki/Gemeine_Schafgarbe',
  language: 'de',
  licence: 'CC-BY-SA-4.0',
};

/** The collaborator, injected — no global stubbing, no import-time binding. */
function loads(result: SpeciesInfoOut | null) {
  return vi.fn(async () => result);
}

function fails() {
  return vi.fn(async () => {
    throw new Error('service unavailable');
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('SpeciesInfo', () => {
  it('shows the description with its photo', async () => {
    render(<SpeciesInfo taxonId={1} canonicalName="Achillea millefolium" onClose={vi.fn()} load={loads(ARTICLE)} />);
    await waitFor(() => expect(screen.getByText(/Korbblütler/)).toBeDefined());
    const image = screen.getByRole('img');
    expect(image.getAttribute('src')).toBe(ARTICLE.thumbnail_url);
    expect(image.getAttribute('alt')).toContain('Gemeine Schafgarbe');
  });

  it('always credits Wikipedia and links back', async () => {
    // CC-BY-SA is a condition of use. A cached copy does not become ours.
    render(<SpeciesInfo taxonId={1} canonicalName="Achillea millefolium" onClose={vi.fn()} load={loads(ARTICLE)} />);
    await waitFor(() => expect(screen.getByText(/CC-BY-SA-4.0/)).toBeDefined());
    const link = screen.getByRole('link', { name: 'Wikipedia' });
    expect(link.getAttribute('href')).toBe(ARTICLE.page_url);
    expect(link.getAttribute('rel')).toContain('noopener');
  });

  it('says when the article shown is not German', async () => {
    // A German user shown English text should know why.
    render(
      <SpeciesInfo taxonId={1} canonicalName="Achillea millefolium" onClose={vi.fn()}
        load={loads({ ...ARTICLE, language: 'en', title: 'Achillea millefolium' })} />,
    );
    await waitFor(() => expect(screen.getByText(/englische/)).toBeDefined());
  });

  it('says plainly when there is no article at all', async () => {
    render(
      <SpeciesInfo taxonId={1} canonicalName="Trigonella coerulescens" onClose={vi.fn()}
        load={loads(null)} />,
    );
    await waitFor(() => expect(screen.getByText(/keinen Wikipedia-Artikel/)).toBeDefined());
  });

  it('degrades rather than breaking when the lookup fails', async () => {
    // A plant list must not break because an external service is down.
    render(
      <SpeciesInfo taxonId={1} canonicalName="Achillea millefolium" onClose={vi.fn()}
        load={fails()} />,
    );
    await waitFor(() => expect(screen.getByText(/nicht geladen werden/)).toBeDefined());
    // The species is still identified — the panel degrades, it does not vanish.
    expect(screen.getByRole('heading', { name: 'Achillea millefolium' })).toBeDefined();
  });

  it('names the species before anything has loaded', async () => {
    // Both the heading and the subtitle carry it at that point, which is why the
    // matcher has to be specific rather than "the text appears somewhere".
    render(
      <SpeciesInfo taxonId={1} canonicalName="Achillea millefolium" onClose={vi.fn()}
        load={loads(ARTICLE)} />,
    );
    expect(screen.getByRole('heading', { name: 'Achillea millefolium' })).toBeDefined();
    await waitFor(() => expect(screen.getByText(/Korbblütler/)).toBeDefined());
  });

  it('renders the extract as text, never as markup', async () => {
    // Untrusted third-party content.
    const { container } = render(
      <SpeciesInfo taxonId={1} canonicalName="X" onClose={vi.fn()}
        load={loads({ ...ARTICLE, extract: 'Ein <script>alert(1)</script> Kraut.' })} />,
    );
    await waitFor(() => expect(screen.getByText(/Kraut/)).toBeDefined());
    expect(container.querySelector('script')).toBeNull();
  });

  it('handles an article with no photo', async () => {
    render(
      <SpeciesInfo taxonId={1} canonicalName="X" onClose={vi.fn()}
        load={loads({ ...ARTICLE, thumbnail_url: null })} />,
    );
    await waitFor(() => expect(screen.getByText(/Korbblütler/)).toBeDefined());
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('fetches once when no loader is injected, even across re-renders', async () => {
    // The bug this pins: an inline default parameter `load = (id) => ...` is a
    // fresh closure on every render, and it is an effect dependency. The effect
    // then cancels and refires itself forever — in the running app this issued
    // ~100 requests to Wikipedia in milliseconds while the panel showed
    // "Wird geladen…". Every other test here injects `load`, which is stable in
    // a test, so none of them could see it. This one exercises the default.
    const calls: string[] = [];
    const fetchStub = vi.fn(async (url: string) => {
      calls.push(String(url));
      if (calls.length > 20) {
        // Terminate a looping implementation loudly instead of hanging the suite.
        throw new Error(`runaway fetch loop: ${calls.length} calls`);
      }
      return {
        ok: true,
        status: 200,
        json: async () => ARTICLE,
      } as Response;
    });
    // The default client binds globalThis.fetch in its constructor, which runs at
    // module import — so the stub has to be in place before the module loads.
    vi.stubGlobal('fetch', fetchStub);
    vi.resetModules();
    const { SpeciesInfo: Fresh } = await import('./SpeciesInfo');

    const { rerender } = render(
      <Fresh taxonId={7} canonicalName="Achillea millefolium" onClose={vi.fn()} />,
    );
    await waitFor(() => expect(screen.getByText(/Korbblütler/)).toBeDefined());

    // A parent re-render must not restart the request.
    rerender(<Fresh taxonId={7} canonicalName="Achillea millefolium " onClose={vi.fn()} />);
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(fetchStub).toHaveBeenCalledTimes(1);
  });

  it('refetches when the species actually changes', async () => {
    // The counterpart: stabilising the default must not freeze the panel on the
    // first species the user clicked.
    const load = vi.fn(async (id: number) => ({ ...ARTICLE, title: `Art ${id}` }));
    const { rerender } = render(
      <SpeciesInfo taxonId={1} canonicalName="A" onClose={vi.fn()} load={load} />,
    );
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Art 1' })).toBeDefined());

    rerender(<SpeciesInfo taxonId={2} canonicalName="B" onClose={vi.fn()} load={load} />);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Art 2' })).toBeDefined());
    expect(load).toHaveBeenCalledTimes(2);
  });

  it('never names two species at once while switching', async () => {
    // Clicking a second plant reuses this component instance, so state survives
    // unless it is cleared. The heading must not keep claiming the previous
    // species while the subtitle already shows the new one.
    let release: (value: SpeciesInfoOut) => void = () => {};
    const load = vi.fn((id: number) =>
      id === 1
        ? Promise.resolve(ARTICLE)
        : new Promise<SpeciesInfoOut>((resolve) => {
            release = resolve;
          }),
    );

    const { rerender } = render(
      <SpeciesInfo taxonId={1} canonicalName="Achillea millefolium" onClose={vi.fn()} load={load} />,
    );
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Gemeine Schafgarbe' })).toBeDefined());

    // Second species selected; its article has not arrived yet.
    rerender(
      <SpeciesInfo taxonId={2} canonicalName="Hordeum secalinum" onClose={vi.fn()} load={load} />,
    );
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Hordeum secalinum' })).toBeDefined(),
    );
    expect(screen.queryByText('Gemeine Schafgarbe')).toBeNull();

    release({ ...ARTICLE, title: 'Roggen-Gerste' });
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Roggen-Gerste' })).toBeDefined());
  });
});

describe('SpeciesInfo — reaching the reader', () => {
  it('brings itself into view when it opens', async () => {
    // It renders under a suggestion list thousands of pixels long. Opening it
    // from the first row put it four screens below the viewport, which reads
    // as the button doing nothing.
    const seen: unknown[] = [];
    Element.prototype.scrollIntoView = function scroll(this: Element, arg?: unknown) {
      seen.push(arg);
    } as typeof Element.prototype.scrollIntoView;

    render(
      <SpeciesInfo
        taxonId={1}
        canonicalName="Salvia pratensis"
        onClose={vi.fn()}
        load={async () => null}
      />,
    );
    await waitFor(() => expect(seen.length).toBeGreaterThan(0));
  });

  it('takes focus, so a keyboard reader lands on it too', async () => {
    render(
      <SpeciesInfo
        taxonId={2}
        canonicalName="Salvia pratensis"
        onClose={vi.fn()}
        load={async () => null}
      />,
    );
    await waitFor(() =>
      expect(document.activeElement?.classList.contains('info-panel')).toBe(true),
    );
  });
});
