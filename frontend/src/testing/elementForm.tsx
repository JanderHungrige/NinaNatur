import { render } from '@testing-library/react';
import { vi } from 'vitest';

import { ElementForm } from '../components/ElementForm';

type Props = Parameters<typeof ElementForm>[0];

/**
 * The form as the details show it: an element with no kind and no name yet.
 * `update` renders it again over a changed store, as a server answer does
 * while it is open.
 */
export function open(props: Partial<Props> = {}) {
  const handlers = {
    onSave: vi.fn(),
    onDelete: vi.fn(),
    onCancel: vi.fn(),
    onFocusTaken: vi.fn(),
  };
  const form = (more: Partial<Props>) => (
    <ElementForm
      heading="Was ist das?"
      kind="other"
      label={null}
      plantings={0}
      shape="polygon"
      roof="unknown"
      roofSource="user"
      roofFallDeg={null}
      roofPitchDeg={null}
      eavesM={null}
      eavesSource={null}
      crownBaseM={null}
      crownBaseSource={null}
      crownFits={null}
      height={null}
      width={null}
      soilType={null}
      moisture={null}
      heightAboveGround={0}
      busy={false}
      takeFocus={false}
      {...handlers}
      {...props}
      {...more}
    />
  );
  const { rerender } = render(form({}));
  return { ...handlers, update: (more: Partial<Props>) => rerender(form(more)) };
}

/** Every note a screen reader hears after a field's name, in order. */
export function notesFor(control: HTMLElement): string[] {
  const ids = control.getAttribute('aria-describedby');
  if (ids === null) return [];
  return ids.split(' ').map((id) => document.getElementById(id)?.textContent ?? '');
}

/** The first of them: where the stored value came from. */
export function noteFor(control: HTMLElement): string | null {
  return notesFor(control)[0] ?? null;
}
