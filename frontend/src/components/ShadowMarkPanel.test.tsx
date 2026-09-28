import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { ShadowMark } from '../api/client';
import { nowLocal } from '../shadowMarks';
import { ShadowMarkLayer } from './ShadowMarkLayer';
import { ShadowMarkPanel } from './ShadowMarkPanel';

function mark(markId: number, elementId: number, reading: ShadowMark['reading'] = {
  altitude: 38, azimuth: 180, rings: [[[0, 0], [2, 0], [2, 5], [0, 5]]], nearest: [1, 5],
  offset_m: 0.8, edge: 'far', model_longer: false, along_m: -0.8, across_m: 0, height_m: -0.63,
  turned_deg: null,
}): ShadowMark {
  return { mark_id: markId, element_id: elementId, x: 1, y: 5.8,
           seen_at: '2026-06-21T09:30:00+00:00', reading };
}

type Props = Parameters<typeof ShadowMarkPanel>[0];

function panel(overrides: Partial<Props> = {}): Props {
  return {
    elementId: 2, canMark: true, marks: [mark(1, 2), mark(2, 9)], seenAt: null,
    onSeenAt: vi.fn(), armed: false, onToggle: vi.fn(), onRemove: vi.fn(), busy: false,
    ...overrides,
  };
}

describe('ShadowMarkPanel — where this thing\'s shadow was seen to end (doc 122)', () => {
  it('lists this element\'s marks with what each found, and not another\'s', () => {
    render(<ShadowMarkPanel {...panel()} />);
    const list = screen.getByRole('list');
    expect(within(list).getAllByRole('listitem')).toHaveLength(1);
    expect(list.textContent).toContain('0,8 m zu kurz');
  });

  it('arms the plan, shows that it is armed, and puts the mark down on a second press', () => {
    const props = panel();
    const { rerender } = render(<ShadowMarkPanel {...props} />);
    const arm = screen.getByRole('button', { name: 'Im Plan markieren' });
    fireEvent.click(arm);
    expect(props.onToggle).toHaveBeenCalledTimes(1);
    rerender(<ShadowMarkPanel {...props} armed />);
    expect(arm.getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByText('Klicke in den Plan, wo die Schattenkante liegt.')).toBeDefined();
    fireEvent.click(arm);
    expect(props.onToggle).toHaveBeenCalledTimes(2);
  });

  it('marks at the moment of the click unless another is typed', () => {
    // It started at the moment the garden was opened (review, 2026-09-28).
    const props = panel();
    const { rerender } = render(<ShadowMarkPanel {...props} />);
    const field = screen.getByLabelText('Gesehen am') as HTMLInputElement;
    expect(field.value).toBe(nowLocal());
    expect(screen.getByText('Jetzt — der Moment des Klicks.')).toBeDefined();
    fireEvent.change(field, { target: { value: '2026-06-21T14:00' } });
    expect(props.onSeenAt).toHaveBeenCalledWith('2026-06-21T14:00');
    rerender(<ShadowMarkPanel {...props} seenAt="2026-06-21T14:00" />);
    expect(field.value).toBe('2026-06-21T14:00');
    expect(screen.getByText('Leeren für jetzt.')).toBeDefined();
  });

  it('keeps the marks of a thing that casts no more, to be forgotten', () => {
    // Made paving, a shed's marks stayed drawn with no way to remove them.
    const props = panel({ canMark: false });
    render(<ShadowMarkPanel {...props} />);
    expect(screen.queryByRole('button', { name: 'Im Plan markieren' })).toBeNull();
    expect(screen.queryByLabelText('Gesehen am')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /Markierung 1 vom .* löschen/ }));
    expect(props.onRemove).toHaveBeenCalledWith(1);
  });

  it('names every delete button apart, though two marks share a minute', () => {
    render(<ShadowMarkPanel {...panel({ marks: [mark(1, 2), mark(3, 2)] })} />);
    const names = screen.getAllByRole('button', { name: /löschen/ })
      .map((button) => button.getAttribute('aria-label'));
    expect(new Set(names).size).toBe(2);
  });

  it('gives the focus to its heading when the button holding it goes', () => {
    const props = panel({ marks: [mark(1, 2), mark(3, 2)] });
    const { rerender } = render(<ShadowMarkPanel {...props} />);
    screen.getByRole('button', { name: /Markierung 1 vom/ }).focus();
    rerender(<ShadowMarkPanel {...props} marks={[mark(3, 2)]} />);
    expect(document.activeElement?.textContent).toBe('Schattenkante');
  });

  it('ignores presses while a request runs, without giving up the focus', () => {
    const props = panel({ busy: true });
    render(<ShadowMarkPanel {...props} />);
    const arm = screen.getByRole('button', { name: 'Im Plan markieren' });
    expect((arm as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(arm);
    expect(props.onToggle).not.toHaveBeenCalled();
  });
});

describe('ShadowMarkLayer — the marks on the plan', () => {
  it('draws the mark, the model\'s edge and the way between, never as a target', () => {
    const at: ShadowMark = { ...mark(1, 2), x: 1.5, y: 6 };
    const { container } = render(<svg><ShadowMarkLayer marks={[at]} /></svg>);
    expect(container.querySelector('.shadow-marks')?.getAttribute('pointer-events')).toBe('none');
    // y is drawn downwards: the plan's north is up.
    expect(container.querySelector('.shadow-mark__cross')?.getAttribute('d'))
      .toBe('M1.2,-6.3L1.8,-5.7M1.2,-5.7L1.8,-6.3');
    expect(container.querySelector('.shadow-mark__edge')?.getAttribute('d'))
      .toBe('M0,0L2,0L2,-5L0,-5Z');
    expect(container.querySelector('.shadow-mark__way')?.getAttribute('d')).toBe('M1.5,-6L1,-5');
    expect(container.querySelectorAll('.shadow-mark__halo')).toHaveLength(2);
  });

  it('draws only the cross where there is nothing to read, and nothing without marks', () => {
    const { container, rerender } = render(<svg><ShadowMarkLayer marks={[mark(1, 2, null)]} /></svg>);
    expect(container.querySelectorAll('.shadow-mark__cross')).toHaveLength(1);
    expect(container.querySelector('.shadow-mark__edge')).toBeNull();
    rerender(<svg><ShadowMarkLayer marks={[]} /></svg>);
    expect(container.querySelector('.shadow-marks')).toBeNull();
  });
});
