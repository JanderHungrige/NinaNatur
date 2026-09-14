import { fireEvent, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  details,
  fakeClient,
  onPlan,
  openWorkspace,
  resetApp,
  stubMatchMedia,
  viewHeading,
} from './testing/appFixtures';
import { garden, richGarden } from './testing/gardens';

/*
 * Doc 88: one selection, whichever way it was reached — the plan, the element
 * list or the details — and the details follow it. Three views onto one
 * selection is the obvious way for them to disagree, and they did: a bed chosen
 * in the list lost its handles, and an element chosen after a bed left the bed
 * marked.
 */

async function open() {
  const client = fakeClient({}, { tok: richGarden(), tok2: garden('tok2', 'Zweitgarten') });
  await openWorkspace(client);
  return client;
}

const bedOnPlan = () => onPlan('polygon[data-element-id="1"]');
const shedOnPlan = () => onPlan('polygon[data-element-id="5"]');
const patchOnPlan = () => onPlan('[data-planting-id="11"]');
const suggestionsShown = () => within(details()).queryByRole('heading', { name: /^Vorschläge/ });

beforeEach(stubMatchMedia);
afterEach(resetApp);

describe('App — one selection, whichever way it was reached', () => {
  it('shows the garden while nothing is selected', async () => {
    await open();
    expect(viewHeading()?.textContent).toBe('Testgarten');
    expect(within(details()).getByRole('heading', { name: 'Gezeichnete Objekte' })).toBeDefined();
    expect(suggestionsShown()).toBeNull();
  });

  it('shows a bed chosen on the plan, marks it there, and asks for its suggestions', async () => {
    const client = await open();
    fireEvent.click(bedOnPlan());
    expect(viewHeading()?.textContent).toBe('Südbeet');
    expect(bedOnPlan().getAttribute('aria-pressed')).toBe('true');
    await within(details()).findByRole('heading', { name: 'Vorschläge für Südbeet' });
    expect(client.bedSuggestions).toHaveBeenCalledWith('tok', 1, {});
  });

  it('gives a bed chosen in the list the selection the plan gives it, handles included', async () => {
    // The list selected the bed for planting and then took its handles away.
    await open();
    fireEvent.click(within(details()).getByRole('button', { name: /^Blumenbeet/ }));
    expect(viewHeading()?.textContent).toBe('Südbeet');
    expect(bedOnPlan().getAttribute('aria-pressed')).toBe('true');
    expect(document.querySelector('[data-testid="handle-nw"]')).not.toBeNull();
  });

  it('never shows two things as selected: an element chosen after a bed takes over', async () => {
    await open();
    fireEvent.click(bedOnPlan());
    fireEvent.click(shedOnPlan());
    expect(bedOnPlan().getAttribute('aria-pressed')).toBe('false');
    expect(shedOnPlan().getAttribute('aria-pressed')).toBe('true');
    expect(viewHeading()?.textContent).toBe('Gartenhaus');
    expect(suggestionsShown()).toBeNull();
  });

  it('shows a patch chosen on the plan as its species, and nothing else as selected', async () => {
    const client = await open();
    fireEvent.click(bedOnPlan());
    fireEvent.click(patchOnPlan());
    expect(viewHeading()?.textContent).toBe('Salvia pratensis');
    expect(patchOnPlan().classList.contains('cluster--selected')).toBe(true);
    expect(bedOnPlan().getAttribute('aria-pressed')).toBe('false');
    await waitFor(() => expect(client.speciesInfo).toHaveBeenCalledWith(3));
  });

  it('goes back from a patch to its bed, and from the bed to the garden', async () => {
    await open();
    fireEvent.click(patchOnPlan());
    fireEvent.click(within(details()).getByRole('button', { name: 'Zurück zu Südbeet' }));
    expect(viewHeading()?.textContent).toBe('Südbeet');
    expect(bedOnPlan().getAttribute('aria-pressed')).toBe('true');
    fireEvent.click(within(details()).getByRole('button', { name: 'Zurück zum Garten' }));
    expect(viewHeading()?.textContent).toBe('Testgarten');
    expect(bedOnPlan().getAttribute('aria-pressed')).toBe('false');
  });

  it('drops the selection on Escape', async () => {
    await open();
    fireEvent.click(shedOnPlan());
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(shedOnPlan().getAttribute('aria-pressed')).toBe('false');
    expect(viewHeading()?.textContent).toBe('Testgarten');
  });

  it('drops a bed on Escape too, which used to stay selected for planting', async () => {
    await open();
    fireEvent.click(bedOnPlan());
    await within(details()).findByRole('heading', { name: 'Vorschläge für Südbeet' });
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(bedOnPlan().getAttribute('aria-pressed')).toBe('false');
    expect(suggestionsShown()).toBeNull();
  });

  it('leaves the selection alone when Escape is typed into a text field', async () => {
    // A name half typed into the details must not vanish with the view it is in.
    await open();
    fireEvent.click(bedOnPlan());
    await within(details()).findByRole('heading', { name: 'Vorschläge für Südbeet' });
    const field = within(details()).getByLabelText('Pflanze');
    field.focus();
    fireEvent.keyDown(field, { key: 'Escape' });
    expect(bedOnPlan().getAttribute('aria-pressed')).toBe('true');
    expect(viewHeading()?.textContent).toBe('Südbeet');
  });
});
