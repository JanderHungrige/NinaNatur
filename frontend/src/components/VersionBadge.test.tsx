import { describe, expect, it, vi } from 'vitest';

import { NinaNaturClient } from '../api/client';

function respond(body: unknown, status = 200): typeof globalThis.fetch {
  return vi.fn(async () =>
    new Response(JSON.stringify(body), {
      status,
      headers: { 'content-type': 'application/json' },
    }),
  ) as unknown as typeof globalThis.fetch;
}

describe('version', () => {
  it('reads the version the server reports', async () => {
    // Only the server knows which build is running; a version compiled into the
    // bundle would keep claiming the old one after a partial rollout.
    const client = new NinaNaturClient({
      fetch: respond({ status: 'ok', service: 'ninanatur', version: 'V0.5.7' }),
    });
    await expect(client.version()).resolves.toBe('V0.5.7');
  });

  it('falls back rather than showing undefined', async () => {
    const client = new NinaNaturClient({ fetch: respond({ status: 'ok' }) });
    await expect(client.version()).resolves.toBe('dev');
  });

  it('asks the health endpoint, which needs no database', async () => {
    const spy = respond({ version: 'V0.5.7' });
    await new NinaNaturClient({ fetch: spy }).version();
    expect(String(vi.mocked(spy).mock.calls[0]?.[0])).toContain('/healthz');
  });

  it('rejects on a failing health check instead of inventing a version', async () => {
    const client = new NinaNaturClient({ fetch: respond({ detail: 'down' }, 503) });
    await expect(client.version()).rejects.toThrow();
  });
});
