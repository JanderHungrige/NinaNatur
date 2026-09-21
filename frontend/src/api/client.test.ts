import { describe, expect, it, vi } from 'vitest';

import { ApiError, NinaNaturClient } from './client';

function respondWith(body: unknown, status = 200): typeof globalThis.fetch {
  return vi.fn(async () =>
    new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    }),
  ) as unknown as typeof globalThis.fetch;
}

describe('NinaNaturClient', () => {
  it('returns the parsed body on success', async () => {
    const client = new NinaNaturClient({ fetch: respondWith({ share_token: 'abc', name: 'G' }) });
    const created = await client.createGarden({ name: 'G', latitude: 52.5, longitude: 13.4 });
    expect(created.share_token).toBe('abc');
  });

  it('throws on a non-2xx, carrying the API reason', async () => {
    // A silently ignored 422 is how a form ends up looking like it worked.
    const client = new NinaNaturClient({
      fetch: respondWith({ detail: 'a bed needs at least 3 points, got 2' }, 422),
    });
    await expect(
      client.addBed('tok', { name: 'Linie', polygon: [[0, 0], [1, 1]] }),
    ).rejects.toThrowError(/at least 3 points/);
  });

  it('exposes the status on the thrown error', async () => {
    const client = new NinaNaturClient({ fetch: respondWith({ detail: 'nope' }, 500) });
    await expect(client.createGarden({ name: 'x', latitude: 0, longitude: 0 })).rejects.toSatisfy(
      (error: unknown) => error instanceof ApiError && error.status === 500,
    );
  });

  it('treats an unknown share token as null, not as an error', async () => {
    // A stale share link is a normal thing for a user to hit.
    const client = new NinaNaturClient({ fetch: respondWith({ detail: 'no such garden' }, 404) });
    await expect(client.getGarden('gone')).resolves.toBeNull();
  });

  it('still throws for non-404 failures on the same call', async () => {
    const client = new NinaNaturClient({ fetch: respondWith({ detail: 'boom' }, 503) });
    await expect(client.getGarden('tok')).rejects.toThrowError(ApiError);
  });

  it('keeps null values null instead of coercing them', async () => {
    // The backend went to some trouble to make "unknown" distinguishable from
    // zero; turning it into 0 here would throw that away at the last step.
    const client = new NinaNaturClient({
      fetch: respondWith({
        share_token: 't', name: 'G', latitude: 52.5, longitude: 13.4,
        created_at: '', updated_at: '', obstacles: [],
        beds: [{
          bed_id: 1, name: 'Beet', polygon: [], soil_type: null, moisture: null, observed_colours: {},
          ellenberg_l: null, ellenberg_m: null, ellenberg_n: null, ellenberg_r: null,
          sun_hours: null, light_computed_at: null,
        }],
      }),
    });
    const garden = await client.getGarden('t');
    expect(garden?.beds[0]?.ellenberg_l).toBeNull();
  });

  it('handles a 204 without trying to parse a body', async () => {
    const client = new NinaNaturClient({ fetch: respondWith(null, 204) });
    await expect(client.deleteGarden('tok')).resolves.toBeUndefined();
  });

  it('encodes the token so a hostile one cannot alter the path', async () => {
    const spy = respondWith({});
    const client = new NinaNaturClient({ fetch: spy });
    await client.getGarden('../../admin');
    expect(vi.mocked(spy).mock.calls[0]?.[0]).toContain('%2F');
  });

  it('asks for fifty suggestions for a bed unless told otherwise', async () => {
    // Doc 90: the list shows a window of them; the route allows a hundred.
    const spy = respondWith({ bed_id: 1, items: [], woody: [] });
    const client = new NinaNaturClient({ fetch: spy });
    await client.bedSuggestions('tok', 1);
    expect(String(vi.mocked(spy).mock.calls[0]?.[0])).toContain('limit=50');
  });

  it('sends "Gehölze ausblenden" as include_trees=false, and nothing by default', async () => {
    // The server's default is true since Wave 6. The client used to send only
    // `true`, so switching woody plants off never reached the server at all.
    const spy = respondWith({ bed_id: 1, items: [], woody: [] });
    const client = new NinaNaturClient({ fetch: spy });
    await client.bedSuggestions('tok', 1, { includeTrees: false });
    await client.bedSuggestions('tok', 1, {});
    expect(String(vi.mocked(spy).mock.calls[0]?.[0])).toContain('include_trees=false');
    expect(String(vi.mocked(spy).mock.calls[1]?.[0])).not.toContain('include_trees');
  });

  it('omits undefined query parameters rather than sending "undefined"', async () => {
    const spy = respondWith({ total: 0, limit: 50, offset: 0, items: [] });
    const client = new NinaNaturClient({ fetch: spy });
    await client.searchPlants({ light: 7, colour: undefined });
    const url = String(vi.mocked(spy).mock.calls[0]?.[0]);
    expect(url).toContain('light=7');
    expect(url).not.toContain('colour');
  });
});
