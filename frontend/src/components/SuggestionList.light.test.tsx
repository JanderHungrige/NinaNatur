import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { BedSuggestions } from '../api/client';
import { SuggestionList } from './SuggestionList';

/*
 * What the list says about the light it was ranked by (owner review #9). The
 * header used to claim "gewertet nach den Standortwerten dieses Beetes" for a
 * bed whose light had never been computed, where the list rested on the soil
 * alone — the likeliest reason a half-shade plant was offered for full sun.
 */

function suggestions(overrides: Partial<BedSuggestions> = {}): BedSuggestions {
  return {
    bed_id: 1,
    bed_name: 'Südbeet',
    site_axes: { ellenberg_m: 5 },
    total: 1,
    items: [],
    woody: [],
    woody_total: 0,
    filters: {},
    light_state: 'current',
    ...overrides,
  } as BedSuggestions;
}

function show(overrides: Partial<BedSuggestions>, props: { busy?: boolean; shade?: boolean } = {}) {
  const onComputeShade = vi.fn();
  render(
    <SuggestionList
      suggestions={suggestions(overrides)}
      includeTrees
      onPlant={vi.fn()}
      onShowInfo={vi.fn()}
      busy={props.busy ?? false}
      {...(props.shade === false ? {} : { onComputeShade })}
    />,
  );
  return onComputeShade;
}

const button = () => screen.queryByRole('button', { name: 'Schatten berechnen' });

describe('SuggestionList and the light', () => {
  it('says the list rests on the soil alone when the light was never computed', () => {
    show({ light_state: 'missing' });
    expect(screen.getByText(/Licht noch nicht berechnet — die Liste berücksichtigt nur den Boden/))
      .toBeDefined();
    expect(screen.queryByText(/gewertet nach den Standortwerten/)).toBeNull();
  });

  it('offers to compute the shade, and asks for it once', () => {
    const onComputeShade = show({ light_state: 'missing' });
    fireEvent.click(button()!);
    expect(onComputeShade).toHaveBeenCalledTimes(1);
  });

  it('says when the light is older than the last change, and offers the same button', () => {
    const onComputeShade = show({ light_state: 'stale' });
    expect(screen.getByText(/Schatten ist nicht mehr aktuell/))
      .toBeDefined();
    expect(screen.queryByText(/gewertet nach den Standortwerten/)).toBeNull();
    fireEvent.click(button()!);
    expect(onComputeShade).toHaveBeenCalledTimes(1);
  });

  it('claims the whole site, and offers nothing, when the light is current', () => {
    show({ light_state: 'current' });
    expect(screen.getByText(/gewertet nach den Standortwerten dieses Beetes/)).toBeDefined();
    expect(screen.queryByText(/nicht berechnet/)).toBeNull();
    expect(button()).toBeNull();
  });

  it('keeps the button in reach while a request runs, and ignores it', () => {
    // Doc 88, rule 11: a button disabled under the keyboard's focus throws the
    // focus to the page — and pressing it twice would start two rebuilds.
    const onComputeShade = show({ light_state: 'missing' }, { busy: true });
    const shade = button()!;
    shade.focus();
    expect((shade as HTMLButtonElement).disabled).toBe(false);
    expect(shade.getAttribute('aria-disabled')).toBe('true');
    fireEvent.click(shade);
    expect(onComputeShade).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(shade);
  });

  it('still says what it could not rank by where there is no button to offer', () => {
    show({ light_state: 'missing' }, { shade: false });
    expect(screen.getByText(/Licht noch nicht berechnet/)).toBeDefined();
    expect(button()).toBeNull();
  });

  it('counts the species the light left out', () => {
    show({ filters: { light: { matched: 2800, unknown: 41, excluded: 1204 } } });
    expect(screen.getByText(/1\.204 Arten, denen das Licht hier nicht passt, sind ausgeblendet/))
      .toBeDefined();
  });

  it('counts one in the singular, and none not at all', () => {
    show({ filters: { light: { matched: 9, unknown: 0, excluded: 1 } } });
    expect(screen.getByText(/1 Art, der das Licht hier nicht passt, ist ausgeblendet/)).toBeDefined();
  });

  it('says nothing about the light cut when it removed nothing', () => {
    show({ filters: { light: { matched: 9, unknown: 2, excluded: 0 } } });
    expect(screen.queryByText(/nicht passt/)).toBeNull();
  });
});
