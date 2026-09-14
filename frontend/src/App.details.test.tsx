import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  details,
  fakeClient,
  onPlan,
  openWorkspace,
  resetApp,
  stubMatchMedia,
  viewHeading,
} from './testing/appFixtures';
import { bed, planting, richGarden, shed } from './testing/gardens';

/* Doc 88: what each view of the details shows, and where the focus goes. */

async function open(overrides: Record<string, unknown> = {}) {
  const client = fakeClient(overrides, { tok: richGarden() });
  await openWorkspace(client);
  return client;
}

const bedOnPlan = () => onPlan('polygon[data-element-id="1"]');
const shedOnPlan = () => onPlan('polygon[data-element-id="5"]');

beforeEach(stubMatchMedia);
afterEach(resetApp);

describe('App — what the details show', () => {
  it('names the element it is about, and what it covers', async () => {
    // Two shapes lying on top of each other take the same click. The name and
    // the area say which one is being described before anything is changed.
    await open();
    fireEvent.click(shedOnPlan());
    expect(viewHeading()?.textContent).toBe('Gartenhaus');
    expect(details().textContent).toMatch(/Schuppen, 4,0 m²/);
    expect(within(details()).getByRole('region', { name: 'Was ist das?' })).toBeDefined();
  });

  it('says what a bed is and what light it gets, with its form folded away', async () => {
    await open();
    fireEvent.click(bedOnPlan());
    expect(details().textContent).toMatch(/Blumenbeet, 6,0 m²/);
    expect(details().textContent).toMatch(/6\.4 h\/Tag/);
    const edit = within(details()).getByRole('button', { name: 'Beet bearbeiten' });
    expect(edit.getAttribute('aria-expanded')).toBe('false');
    expect(within(details()).queryByLabelText('Art')).toBeNull();
  });

  it('shows a patch the catalogue does not know by its own name, with no species panel', async () => {
    const unknown = richGarden({
      beds: [bed({ plantings: [planting({ taxon_id: null, canonical_name: null, raw_name: 'Omas Rose' })] })],
    });
    const client = fakeClient({}, { tok: unknown });
    await openWorkspace(client);
    fireEvent.click(onPlan('[data-planting-id="11"]'));
    expect(viewHeading()?.textContent).toBe('Omas Rose');
    expect(details().textContent).toMatch(/nicht im Katalog/);
    expect(client.speciesInfo).not.toHaveBeenCalled();
  });
});

describe('App — asking about an element, and where the focus goes', () => {
  it('puts the focus in the form when an element is asked about', async () => {
    // Right-click, Shift+F10 or the context-menu key (doc 51): the question
    // lands where it can be answered.
    await open();
    fireEvent.contextMenu(shedOnPlan());
    expect(document.activeElement).toBe(within(details()).getByLabelText('Art'));
  });

  it('unfolds a bed’s form when the bed is asked about, and puts the focus there', async () => {
    // The bed's suggestions start loading at the same moment; the form must
    // still be able to take the focus while they do.
    await open();
    fireEvent.keyDown(bedOnPlan(), { key: 'F10', shiftKey: true });
    const kind = within(details()).getByLabelText('Art') as HTMLSelectElement;
    expect(document.activeElement).toBe(kind);
    expect(kind.value).toBe('bed');
  });

  it('shows what was chosen on the plan without taking the focus off the plan', async () => {
    await open();
    const shape = shedOnPlan();
    shape.focus();
    fireEvent.click(shape);
    expect(viewHeading()?.textContent).toBe('Gartenhaus');
    expect(document.activeElement).toBe(shedOnPlan());
  });

  it('moves the focus to the new view’s heading when the choice was made in the details', async () => {
    await open();
    const row = within(details()).getByRole('button', { name: /^Schuppen/ });
    row.focus();
    fireEvent.click(row);
    expect(viewHeading()?.textContent).toBe('Gartenhaus');
    expect(document.activeElement).toBe(viewHeading());
  });

  it('opens a new view at its top, whatever the last one was scrolled to', async () => {
    // Measured on the preview (V0.20.158): a patch chosen after planting from
    // the suggestions opened 190 px down, its heading out of sight. The details
    // scroll in themselves, and they kept the last view's offset.
    await open();
    fireEvent.click(bedOnPlan());
    let top = 844;
    Object.defineProperty(details(), 'scrollTop', {
      configurable: true,
      get: () => top,
      set: (value: number) => {
        top = value;
      },
    });
    fireEvent.click(onPlan('[data-planting-id="11"]'));
    expect(viewHeading()?.textContent).toBe('Salvia pratensis');
    expect(top).toBe(0);
  });
});

describe('App — changing things from the details', () => {
  it('saves an element under its own id, stays on it, and says so', async () => {
    const renamed = richGarden({ obstacles: [shed({ label: 'Werkzeughaus' })] });
    const client = await open({ editObstacle: vi.fn(async () => renamed) });
    fireEvent.click(shedOnPlan());
    fireEvent.change(within(details()).getByLabelText('Bezeichnung'), {
      target: { value: 'Werkzeughaus' },
    });
    fireEvent.click(within(details()).getByRole('button', { name: 'Übernehmen' }));
    await screen.findByText('Schuppen gespeichert.');
    expect(client.editObstacle).toHaveBeenCalledWith(
      'tok',
      5,
      expect.objectContaining({ kind: 'shed', label: 'Werkzeughaus' }),
    );
    expect(viewHeading()?.textContent).toBe('Werkzeughaus');
  });

  it('turns an element into a bed once it is called Blumenbeet, and asks for its suggestions', async () => {
    // Draw first, say what it is afterwards: a rectangle becomes a bed by being
    // called one, and a bed is there to be planted.
    const asBed = bed({
      bed_id: 5, name: 'Beet 2', label: 'Gartenhaus', polygon: [[5, -1], [7, -1], [7, 1], [5, 1]],
    });
    const becameBed = richGarden({ beds: [bed({ plantings: [planting()] }), asBed], obstacles: [] });
    const client = await open({ editObstacle: vi.fn(async () => becameBed) });
    fireEvent.click(shedOnPlan());
    fireEvent.change(within(details()).getByLabelText('Art'), { target: { value: 'bed' } });
    fireEvent.click(within(details()).getByRole('button', { name: 'Übernehmen' }));
    await waitFor(() => expect(client.bedSuggestions).toHaveBeenCalledWith('tok', 5, {}));
    expect(viewHeading()?.textContent).toBe('Beet 2');
  });

  it('marks the patch that was just planted on the plan, and stays on the bed', async () => {
    const sambucus = planting({ planting_id: 12, taxon_id: 7, canonical_name: 'Sambucus nigra' });
    const planted = richGarden({ beds: [bed({ plantings: [planting(), sambucus] })] });
    await open({ plant: vi.fn(async () => planted) });
    fireEvent.click(bedOnPlan());
    fireEvent.click(await within(details()).findByRole('button', { name: 'Sambucus nigra pflanzen' }));
    await waitFor(() =>
      expect(onPlan('[data-planting-id="12"]').classList.contains('cluster--fresh')).toBe(true),
    );
    expect(onPlan('[data-planting-id="11"]').classList.contains('cluster--fresh')).toBe(false);
    expect(viewHeading()?.textContent).toBe('Südbeet');
  });
});
