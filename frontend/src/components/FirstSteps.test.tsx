import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { bed, garden, lightMap } from '../testing/gardens';
import { FirstSteps, stepsDone } from './FirstSteps';

type Props = Parameters<typeof FirstSteps>[0];

/** The steps for a garden nobody has set up yet, unless told otherwise. */
function steps(props: Partial<Props> = {}) {
  const handlers = { onSaveSoil: vi.fn(), onComputeShade: vi.fn(), onDrawBed: vi.fn() };
  render(
    <FirstSteps
      soilType={null}
      moisture={null}
      hasMap={false}
      beds={0}
      busy={false}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
}

const step = (n: number): HTMLElement => {
  const item = screen.getAllByRole('listitem')[n - 1];
  if (item === undefined) throw new Error(`there is no step ${n}`);
  return item;
};

describe('FirstSteps', () => {
  it('names three steps in order, and says in words which are open', () => {
    // Doc 89: open or done is said, not only coloured or ticked.
    steps();
    expect(screen.getByRole('region', { name: 'Drei Schritte zum Anfang' })).toBeDefined();
    expect(screen.getAllByRole('listitem')).toHaveLength(3);
    expect(step(1).textContent).toMatch(/Boden/);
    expect(step(2).textContent).toMatch(/Schatten berechnen/);
    expect(step(3).textContent).toMatch(/Erstes Beet/);
    for (const n of [1, 2, 3]) expect(step(n).textContent).toMatch(/offen/);
  });

  it('asks the soil in step one as doc 48 asks it: once, with a way to look it up', () => {
    steps();
    expect(within(step(1)).getByLabelText('Boden')).toBeDefined();
    expect(within(step(1)).getByRole('link', { name: /nachschlagen/ })).toBeDefined();
  });

  it('computes the shade from step two', () => {
    const { onComputeShade } = steps();
    fireEvent.click(within(step(2)).getByRole('button', { name: 'Schatten berechnen' }));
    expect(onComputeShade).toHaveBeenCalledTimes(1);
  });

  it('arms the tool for the first bed from step three', () => {
    const { onDrawBed } = steps();
    fireEvent.click(within(step(3)).getByRole('button', { name: 'Beet zeichnen' }));
    expect(onDrawBed).toHaveBeenCalledTimes(1);
  });

  it('says a done step is done, and offers nothing more in it', () => {
    steps({ soilType: 'loam', moisture: 'fresh', hasMap: true, beds: 2 });
    for (const n of [1, 2, 3]) expect(step(n).textContent).toMatch(/erledigt/);
    expect(within(step(1)).getByText('lehmig, frisch')).toBeDefined();
    expect(within(step(2)).queryByRole('button', { name: 'Schatten berechnen' })).toBeNull();
    expect(within(step(3)).queryByRole('button', { name: 'Beet zeichnen' })).toBeNull();
  });

  it('keeps its buttons in reach while a request runs, and ignores them', () => {
    // A disabled button cannot hold the focus (doc 88, rule 11).
    const { onComputeShade } = steps({ busy: true });
    const compute = within(step(2)).getByRole('button', { name: 'Schatten berechnen' }) as HTMLButtonElement;
    expect(compute.disabled).toBe(false);
    expect(compute.getAttribute('aria-disabled')).toBe('true');
    fireEvent.click(compute);
    expect(onComputeShade).not.toHaveBeenCalled();
  });

  it('says the shade is being computed while it is', () => {
    // The longest wait in the garden; a button that just greys out says nothing.
    steps({ busy: true, computing: true });
    const compute = within(step(2)).getByRole('button', { name: 'Wird berechnet…' });
    expect(compute.querySelector('.working__spinner')?.getAttribute('aria-hidden')).toBe('true');
  });
});

describe('stepsDone — read from the garden, not from anything stored', () => {
  it('has every step open for a garden nobody has set up', () => {
    expect(stepsDone(garden('tok', 'G', { beds: [] }), null)).toEqual({
      soil: false, shade: false, bed: false, all: false,
    });
  });

  it('has every step done once the soil is said, a map exists and a bed is drawn', () => {
    const ready = garden('tok', 'G', { soil_type: 'loam', moisture: 'fresh', beds: [bed()] });
    expect(stepsDone(ready, lightMap())).toEqual({ soil: true, shade: true, bed: true, all: true });
  });

  it('needs both halves of the soil answer', () => {
    expect(stepsDone(garden('tok', 'G', { soil_type: 'loam' }), lightMap()).soil).toBe(false);
  });
});
