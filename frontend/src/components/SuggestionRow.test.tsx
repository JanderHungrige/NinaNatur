import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { BedSuggestions } from '../api/client';
import { SuggestionRow } from './SuggestionRow';

type Suggestion = BedSuggestions['items'][number];

function item(overrides: Partial<Suggestion> = {}): Suggestion {
  return {
    taxon_id: 7,
    canonical_name: 'Sambucus nigra',
    family: 'Adoxaceae',
    height_max_m: 6,
    flowering_start_month: 6,
    flowering_end_month: 7,
    flower_colour: 'white',
    colour_known: true,
    bird_partners: null,
    space_m2: null,
    fits_bed: true,
    fit: { score: 0.9, axes: {} },
    ...overrides,
  } as Suggestion;
}

function row(props: Partial<Parameters<typeof SuggestionRow>[0]> = {}) {
  const handlers = { onPlant: vi.fn(async () => {}), onShowInfo: vi.fn() };
  render(
    <ul role="list">
      <SuggestionRow
        item={item()}
        index={2}
        setsize={50}
        top={112}
        tabbable
        extraLine={false}
        busy={false}
        {...handlers}
        {...props}
      />
    </ul>,
  );
  return handlers;
}

describe('SuggestionRow', () => {
  it('names the species, and says its colour in German beside a dot', () => {
    row({ item: item({ flower_colour: 'brown' }) });
    expect(screen.getByText('Sambucus nigra')).toBeDefined();
    expect(screen.getByText('braun')).toBeDefined();
    expect(document.querySelector('.suggestion-row__dot')).not.toBeNull();
    expect(document.querySelector('.suggestion-row__dot--unknown')).toBeNull();
  });

  it('draws an unknown colour as a neutral dot, and says so', () => {
    // Doc 15: a suggestion without a colour shows neutral, with a label.
    row({ item: item({ flower_colour: null }) });
    expect(screen.getByText('Farbe unbekannt')).toBeDefined();
    expect(document.querySelector('.suggestion-row__dot--unknown')).not.toBeNull();
  });

  it('marks the gardener’s own colour as theirs', () => {
    row({ item: item({ flower_colour: null, observed_colour: 'yellow' }) });
    expect(screen.getByText('gelb (von dir)')).toBeDefined();
  });

  it('shows the flowering months as a strip, in words for a screen reader', () => {
    row();
    expect(screen.getByRole('img', { name: 'Blüte Juni bis Juli' })).toBeDefined();
  });

  it('names the weakest axis on the fit badge, and still says every axis', () => {
    const axes = {
      ellenberg_l: { band: 'optimal' },
      ellenberg_m: { band: 'borderline' },
    } as unknown as Suggestion['fit']['axes'];
    row({ item: item({ fit: { score: 0.6, axes } }) });
    const badge = screen.getByText('Feuchte grenzwertig').closest('.suggestion-row__fit');
    expect(badge?.getAttribute('title')).toBe('Licht optimal · Feuchte grenzwertig');
    // What the badge leaves out is not lost to a screen reader.
    expect(badge?.querySelector('.sr-only')?.textContent).toBe('Licht optimal, Feuchte grenzwertig');
  });

  it('shows no badge when no axis was read', () => {
    row();
    expect(document.querySelector('.suggestion-row__fit')).toBeNull();
  });

  it('prices a plant too large for the bed, and counts the birds that eat it', () => {
    // Doc 25: shown, not hidden; counted beside the insect score, not in it.
    row({ item: item({ fits_bed: false, space_m2: 201.1, bird_partners: 100 }), extraLine: true });
    expect(screen.getByText(/braucht ~201 m²/)).toBeDefined();
    expect(screen.getByText(/100 Vogelarten als Nahrung/)).toBeDefined();
    expect(screen.getByRole('listitem').classList.contains('suggestion-row--extra')).toBe(true);
  });

  it('opens what is known about the species from its name', () => {
    const { onShowInfo } = row();
    fireEvent.click(screen.getByRole('button', { name: 'Informationen zu Sambucus nigra' }));
    expect(onShowInfo).toHaveBeenCalledWith(7, 'Sambucus nigra', 'white');
  });

  it('plants the species it stands for', () => {
    const { onPlant } = row();
    fireEvent.click(screen.getByRole('button', { name: 'Sambucus nigra pflanzen' }));
    expect(onPlant).toHaveBeenCalledWith(7, 'Sambucus nigra');
  });

  it('keeps its plant button in reach while a request runs, and ignores it', () => {
    // Feature 2 found this on the preview (V0.20.158): a disabled Pflanzen threw
    // the keyboard's focus to the page the moment it was pressed.
    const { onPlant } = row({ busy: true });
    const plant = screen.getByRole('button', { name: 'Sambucus nigra pflanzen' }) as HTMLButtonElement;
    plant.focus();
    expect(plant.disabled).toBe(false);
    expect(plant.getAttribute('aria-disabled')).toBe('true');
    fireEvent.click(plant);
    expect(onPlant).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(plant);
  });

  it('is in the tab order only while it is the list’s stop', () => {
    row({ tabbable: false });
    expect(screen.getByRole('listitem').tabIndex).toBe(-1);
    for (const button of screen.getAllByRole('button')) expect(button.tabIndex).toBe(-1);
  });

  it('says where it stands in the whole list, and stands there', () => {
    row();
    const listed = screen.getByRole('listitem');
    expect(listed.getAttribute('aria-posinset')).toBe('3');
    expect(listed.getAttribute('aria-setsize')).toBe('50');
    expect(listed.style.top).toBe('112px');
    expect(listed.tabIndex).toBe(0);
    for (const button of screen.getAllByRole('button')) expect(button.tabIndex).toBe(0);
  });
});
