/**
 * Thin typed wrapper over the generated API types.
 *
 * Everything it knows about response shapes comes from `types.ts`, which is
 * generated from the backend's OpenAPI schema. Nothing here restates a shape by
 * hand: a hand-copied type compiles fine while drifting from the API, and the
 * drift only shows up at runtime as `undefined` where a field was renamed.
 */
import type { components } from './types';

export type GardenOut = components['schemas']['GardenOut'];
export type GardenCreated = components['schemas']['GardenCreated'];
export type BedOut = components['schemas']['BedOut'];
export type PlantSearchResponse = components['schemas']['PlantSearchResponse'];
export type PlantSummary = components['schemas']['PlantSummary'];
export type TimelineOut = components['schemas']['TimelineOut'];
export type BedSuggestions = components['schemas']['BedSuggestions'];
export type MonthOut = components['schemas']['MonthOut'];
export type ScoreOut = components['schemas']['ScoreOut'];
export type ImprovementsOut = components['schemas']['ImprovementsOut'];
export type ChangeOut = components['schemas']['ChangeOut'];
export type SpeciesInfoOut = components['schemas']['SpeciesInfoOut'];

/** A non-2xx response, carrying whatever reason the API gave. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(`${status}: ${detail}`);
    this.name = 'ApiError';
  }
}

type FetchLike = typeof globalThis.fetch;

/**
 * A plant search. Every field is explicitly `| undefined` rather than merely
 * optional: under `exactOptionalPropertyTypes` a caller assembling a query from
 * a form has undefined values in hand, and forcing them to strip the keys first
 * would push that chore onto every call site.
 */
/** What the user asked the catalogue for. Every field is removable in the UI. */
export interface SuggestionFilters {
  colour?: string | undefined;
  heightMax?: number | undefined;
  floweringMonth?: number | undefined;
  growthForm?: string | undefined;
  includeUnknown?: boolean | undefined;
  includeTrees?: boolean | undefined;
}

export interface PlantQuery {
  light?: number | undefined;
  moisture?: number | undefined;
  nutrients?: number | undefined;
  reaction?: number | undefined;
  height_max?: number | undefined;
  colour?: string | undefined;
  limit?: number | undefined;
}

export interface ClientOptions {
  baseUrl?: string;
  fetch?: FetchLike;
}

/** Pull the API's `detail` out of an error body, whatever shape it arrived in. */
async function readDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === 'object' && 'detail' in body) {
      const { detail } = body as { detail: unknown };
      return typeof detail === 'string' ? detail : JSON.stringify(detail);
    }
  } catch {
    // Body was not JSON — fall through to the status text.
  }
  return response.statusText || 'request failed';
}

export class NinaNaturClient {
  private readonly baseUrl: string;
  private readonly doFetch: FetchLike;

  constructor(options: ClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? '').replace(/\/$/, '');
    this.doFetch = options.fetch ?? globalThis.fetch.bind(globalThis);
  }

  /**
   * Every request goes through here so a non-2xx can never be mistaken for
   * success. A silently ignored 422 is how a form ends up looking like it worked.
   */
  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await this.doFetch(`${this.baseUrl}${path}`, {
      headers: { 'content-type': 'application/json' },
      ...init,
    });
    if (!response.ok) {
      throw new ApiError(response.status, await readDetail(response));
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  /**
   * The deployed version, from the health endpoint.
   *
   * Reads it rather than compiling it in: the bundle and the image are built
   * together, but only the server knows which build is actually running — and a
   * version baked into the frontend would keep claiming the old one after a
   * partial rollout.
   */
  async version(): Promise<string> {
    const body = await this.request<{ version?: string }>('/healthz');
    return typeof body.version === 'string' ? body.version : 'dev';
  }

  async createGarden(input: {
    name: string;
    latitude: number;
    longitude: number;
  }): Promise<GardenCreated> {
    return this.request<GardenCreated>('/api/v1/gardens', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  /**
   * Returns `null` for an unknown token rather than throwing: a share link that
   * no longer resolves is a normal thing for a user to hit, not an exception.
   */
  async getGarden(token: string): Promise<GardenOut | null> {
    try {
      return await this.request<GardenOut>(`/api/v1/gardens/${encodeURIComponent(token)}`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return null;
      }
      throw error;
    }
  }

  async addBed(
    token: string,
    bed: {
      name: string;
      polygon: number[][];
      soil_type?: string | null;
      moisture?: string | null;
    },
  ): Promise<GardenOut> {
    return this.request<GardenOut>(`/api/v1/gardens/${encodeURIComponent(token)}/beds`, {
      method: 'POST',
      body: JSON.stringify(bed),
    });
  }

  async addObstacle(
    token: string,
    obstacle: { kind: string; x: number; y: number; radius: number; height: number },
  ): Promise<GardenOut> {
    return this.request<GardenOut>(`/api/v1/gardens/${encodeURIComponent(token)}/obstacles`, {
      method: 'POST',
      body: JSON.stringify(obstacle),
    });
  }

  async deleteGarden(token: string): Promise<void> {
    await this.request<void>(`/api/v1/gardens/${encodeURIComponent(token)}`, {
      method: 'DELETE',
    });
  }

  /** Suggestions for one bed, ranked against its own conditions. */
  async bedSuggestions(
    token: string,
    bedId: number,
    options: { limit?: number } & SuggestionFilters = {},
  ): Promise<BedSuggestions> {
    const params = new URLSearchParams({ limit: String(options.limit ?? 20) });
    // Only what the user actually chose is sent. An omitted filter and a filter
    // left at its default are the same request, so the server's defaults stay
    // the single source of truth and the URL says what was asked.
    const chosen: Array<[string, string | number | boolean | undefined]> = [
      ['colour', options.colour],
      ['height_max', options.heightMax],
      ['flowering_month', options.floweringMonth],
      ['growth_form', options.growthForm],
      ['include_unknown', options.includeUnknown === true ? true : undefined],
      ['include_trees', options.includeTrees === true ? true : undefined],
    ];
    for (const [key, value] of chosen) {
      if (value !== undefined && value !== '') {
        params.set(key, String(value));
      }
    }
    return this.request<BedSuggestions>(
      `/api/v1/gardens/${encodeURIComponent(token)}/beds/${bedId}/suggestions?${params.toString()}`,
    );
  }

  /** Change what a bed is. The server redoes its light and returns the garden. */
  async editBed(
    token: string,
    bedId: number,
    changes: Record<string, string | number>,
  ): Promise<GardenOut> {
    return this.request<GardenOut>(
      `/api/v1/gardens/${encodeURIComponent(token)}/beds/${bedId}`,
      { method: 'PATCH', body: JSON.stringify(changes) },
    );
  }

  async editObstacle(
    token: string,
    obstacleId: number,
    changes: Record<string, string | number>,
  ): Promise<GardenOut> {
    return this.request<GardenOut>(
      `/api/v1/gardens/${encodeURIComponent(token)}/obstacles/${obstacleId}`,
      { method: 'PATCH', body: JSON.stringify(changes) },
    );
  }

  async plant(
    token: string,
    bedId: number,
    taxonId: number,
    quantity = 1,
  ): Promise<GardenOut> {
    return this.request<GardenOut>(
      `/api/v1/gardens/${encodeURIComponent(token)}/beds/${bedId}/plantings`,
      { method: 'POST', body: JSON.stringify({ taxon_id: taxonId, quantity }) },
    );
  }

  /**
   * A description and photo for one species, or null when there is no article.
   *
   * Null rather than throwing: a missing Wikipedia page is a normal outcome for
   * an obscure species, not an error the user should see as one.
   */
  async speciesInfo(taxonId: number): Promise<SpeciesInfoOut | null> {
    try {
      return await this.request<SpeciesInfoOut>(`/api/v1/plants/${taxonId}/info`);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return null;
      }
      throw error;
    }
  }

  /** What this planting is worth to insects, with its components. */
  async score(token: string): Promise<ScoreOut> {
    return this.request<ScoreOut>(`/api/v1/gardens/${encodeURIComponent(token)}/score`);
  }

  /** What to plant, and what it would gain. */
  async improvements(token: string): Promise<ImprovementsOut> {
    return this.request<ImprovementsOut>(
      `/api/v1/gardens/${encodeURIComponent(token)}/improvements`,
    );
  }

  /** The bloom year. `forage` weights by insect partners; false counts blooms. */
  async timeline(token: string, forage = true): Promise<TimelineOut> {
    return this.request<TimelineOut>(
      `/api/v1/gardens/${encodeURIComponent(token)}/timeline?forage=${String(forage)}`,
    );
  }

  /** Plant suggestions for a bed's site axes. */
  async searchPlants(query: PlantQuery): Promise<PlantSearchResponse> {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null) {
        params.set(key, String(value));
      }
    }
    return this.request<PlantSearchResponse>(`/api/v1/plants?${params.toString()}`);
  }
}
