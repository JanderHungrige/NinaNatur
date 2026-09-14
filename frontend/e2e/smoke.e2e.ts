import { expect, type Locator, type Page, test } from '@playwright/test';

/*
 * Wave 23's acceptance, measured where there is layout: the core loop — choose
 * a bed, plant a species, see it on the plan — on a garden whose bed has fifty
 * suggestions, while the page never scrolls, is never taller than the window,
 * and the plan keeps at least 40 % of the window's height. jsdom cannot lay a
 * page out; vitest covers the structure and the keyboard.
 */

interface Numbers {
  scrollY: number;
  documentHeight: number;
  windowHeight: number;
  planShare: number | null;
}

/** The acceptance's three numbers, now. */
const numbers = (page: Page): Promise<Numbers> =>
  page.evaluate(() => {
    const stage = document.querySelector('.canvas-stage')?.getBoundingClientRect();
    return {
      scrollY: Math.round(window.scrollY),
      documentHeight: document.documentElement.scrollHeight,
      windowHeight: window.innerHeight,
      planShare: stage ? Math.round((stage.height / window.innerHeight) * 1000) / 10 : null,
    };
  });

async function holds(page: Page, moment: string): Promise<void> {
  const seen = await numbers(page);
  expect.soft(seen.scrollY, `${moment}: the page scrolled`).toBe(0);
  expect.soft(seen.documentHeight, `${moment}: the page is taller than the window`).toBeLessThanOrEqual(
    seen.windowHeight + 1,
  );
  expect.soft(seen.planShare ?? 0, `${moment}: the plan's share of the window, in per cent`).toBeGreaterThanOrEqual(40);
}

/**
 * A garden of the test's own, with one bed on fresh loam, made from the site's
 * own origin as the page makes one. If its bed cannot be made, the garden goes
 * again at once.
 */
async function makeGarden(page: Page): Promise<{ token: string; suggestions: number }> {
  await page.goto('/');
  return page.evaluate(async () => {
    const json = async (response: Response): Promise<unknown> => {
      // The path without the token: a failed run's message is printed.
      const where = new URL(response.url).pathname.split('/').slice(0, 4).join('/');
      if (!response.ok) throw new Error(`${where} answered ${response.status}`);
      return response.json();
    };
    const created = (await json(
      await fetch('/api/v1/gardens', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'Rauchtest (wird gleich gelöscht)', latitude: 51.2564, longitude: 7.1501 }),
      }),
    )) as { share_token: string };
    const at = `/api/v1/gardens/${encodeURIComponent(created.share_token)}`;
    try {
      const garden = (await json(
        await fetch(`${at}/beds`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: 'Rauchbeet',
            polygon: [[0, 0], [6, 0], [6, 3], [0, 3]],
            soil_type: 'loam',
            moisture: 'fresh',
          }),
        }),
      )) as { beds: { bed_id: number }[] };
      const bed = garden.beds[0]?.bed_id;
      const listed = (await json(await fetch(`${at}/beds/${bed}/suggestions?limit=50`))) as { items: unknown[] };
      return { token: created.share_token, suggestions: listed.items.length };
    } catch (error) {
      await fetch(at, { method: 'DELETE' });
      throw error;
    }
  });
}

const deleteGarden = (page: Page, token: string): Promise<number> =>
  page.evaluate(
    async (t) => (await fetch(`/api/v1/gardens/${encodeURIComponent(t)}`, { method: 'DELETE' })).status,
    token,
  );

/** Whether the patch just planted is on the plan with nothing lying over its middle. */
const patchInSight = (page: Page): Promise<boolean> =>
  page.evaluate(() => {
    const patch = document.querySelector('.cluster--fresh');
    if (patch === null) return false;
    const box = patch.getBoundingClientRect();
    const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
    return top !== null && patch.contains(top);
  });

test('the core loop needs no page scroll, and the plan keeps 40 % of the window', async ({ page, context }, testInfo) => {
  const press = (target: Locator) => (testInfo.project.use.hasTouch === true ? target.tap() : target.click());
  // A page of its own for the garden: the loop's page opens the garden by its
  // address, and a change of hash alone would not load it.
  const setup = await context.newPage();
  const { token, suggestions } = await makeGarden(setup);
  try {
    expect(suggestions, 'suggestions for the fixture bed').toBe(50);
    await page.goto(`/#${token}`);
    await page.locator('aside.inspector [data-view-heading]').waitFor();
    await holds(page, 'opened');

    await press(page.locator('polygon.bed').first());
    const first = page.locator('aside.inspector ul[aria-label="Vorschläge"] li.suggestion-row').first();
    await first.waitFor();
    await holds(page, 'bed chosen');

    const species = ((await first.locator('.suggestion-row__name').textContent()) ?? '').trim();
    const plus = first.locator('.suggestion-row__plant');
    // As a person scrolls the list: until the button stands where it can be reached.
    await plus.evaluate((button) => button.scrollIntoView({ block: 'center' }));
    await press(plus);
    await expect(page.locator('.status-toast__text')).toContainText(`${species} gepflanzt`);
    await expect(page.locator('.cluster--fresh')).toHaveCount(1);
    expect(await patchInSight(page), 'the new patch in sight, with nothing over it').toBe(true);
    await holds(page, 'planted');
  } finally {
    expect(await deleteGarden(setup, token), 'the fixture garden deleted').toBe(204);
  }
});
