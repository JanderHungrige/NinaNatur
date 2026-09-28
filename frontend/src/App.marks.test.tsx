import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { SHADOW_MARK_HINT } from './components/ToolRail';
import {
  details,
  fakeClient,
  onPlan,
  openWorkspace,
  resetApp,
  stubMatchMedia,
  viewHeading,
} from './testing/appFixtures';
import { richGarden, shed } from './testing/gardens';

/* Doc 122, the whole way through the page: a shed's details arm the plan, the
   next click is the mark, and it is drawn. Each piece was tested alone, and a
   one-line break in the wiring between them passed every test (review,
   2026-09-28). */

const shedOnPlan = () => onPlan('polygon[data-element-id="5"]');
const surface = () => screen.getByTestId('canvas-surface');

async function open(garden = richGarden()) {
  const client = fakeClient({}, { tok: garden });
  await openWorkspace(client);
  return client;
}

function arm(): HTMLElement {
  fireEvent.click(shedOnPlan());
  const button = within(details()).getByRole('button', { name: 'Im Plan markieren' });
  fireEvent.click(button);
  return button;
}

beforeEach(stubMatchMedia);
afterEach(resetApp);

describe('App — marking where a shadow ends', () => {
  it('arms the plan from the shed\'s details, and the next click there is its mark', async () => {
    const client = await open();
    const button = arm();
    expect(button.getAttribute('aria-pressed')).toBe('true');
    expect(screen.getAllByText(SHADOW_MARK_HINT).length).toBeGreaterThan(0);

    fireEvent.click(surface(), { clientX: 400, clientY: 300 });

    await waitFor(() => expect(client.markShadow).toHaveBeenCalledWith(
      'tok', expect.objectContaining({ element_id: 5 })));
    await waitFor(() => expect(document.querySelectorAll('.shadow-mark')).toHaveLength(1));
    expect(button.getAttribute('aria-pressed')).toBe('false');
  });

  it('puts the armed mark down on Escape, and leaves the shed chosen', async () => {
    const client = await open();
    const button = arm();

    fireEvent.keyDown(document, { key: 'Escape' });

    expect(button.getAttribute('aria-pressed')).toBe('false');
    expect(viewHeading()?.textContent).toBe('Gartenhaus');
    fireEvent.click(surface(), { clientX: 400, clientY: 300 });
    expect(client.markShadow).not.toHaveBeenCalled();
  });

  it('puts it down when the details go back to the garden, so no click marks the wrong thing',
    async () => {
      const client = await open();
      arm();

      fireEvent.click(within(details()).getByRole('button', { name: 'Zurück zum Garten' }));

      expect(screen.queryAllByText(SHADOW_MARK_HINT)).toHaveLength(0);
      fireEvent.click(surface(), { clientX: 400, clientY: 300 });
      expect(client.markShadow).not.toHaveBeenCalled();
    });

  it('does not ask it of a thing nobody gave a height, which casts nothing', async () => {
    await open(richGarden({ obstacles: [shed({ height: null })] }));
    fireEvent.click(shedOnPlan());
    expect(viewHeading()?.textContent).toBe('Gartenhaus');
    expect(within(details()).queryByRole('region', { name: 'Schattenkante' })).toBeNull();
  });
});
