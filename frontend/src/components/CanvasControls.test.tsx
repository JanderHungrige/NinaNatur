import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { CanvasControls } from './CanvasControls';

type Props = Parameters<typeof CanvasControls>[0];

function controls(props: Partial<Props> = {}) {
  render(
    <CanvasControls
      gridSpacingM={1}
      drawing={false}
      draftPoints={0}
      canUndo={false}
      canRedo={false}
      problem={null}
      onZoomIn={vi.fn()}
      onZoomOut={vi.fn()}
      onFinish={vi.fn()}
      onCancel={vi.fn()}
      onUndo={vi.fn()}
      onRedo={vi.fn()}
      {...props}
    />,
  );
}

describe('CanvasControls', () => {
  it('no longer places a viewpoint: that is the rail’s Standpunkt now', () => {
    // Doc 89. A way of using the plan belongs with the other ways of using it.
    controls();
    expect(screen.queryByRole('button', { name: /Standpunkt/ })).toBeNull();
  });

  it('says how many trees were found, and shows them when asked', () => {
    const onShowFoundTrees = vi.fn();
    controls({ foundTrees: 3, onShowFoundTrees });
    fireEvent.click(screen.getByRole('button', { name: '3 gefundene Bäume' }));
    expect(onShowFoundTrees).toHaveBeenCalledTimes(1);
  });

  it('counts one tree as one', () => {
    controls({ foundTrees: 1, onShowFoundTrees: vi.fn() });
    expect(screen.getByRole('button', { name: '1 gefundener Baum' })).toBeDefined();
  });

  it('offers nothing when nothing was found', () => {
    controls({ foundTrees: 0, onShowFoundTrees: vi.fn() });
    expect(screen.queryByRole('button', { name: /gefunden/ })).toBeNull();
  });
});
