import { fetchStationsFromIrctc, fetchStationCodeFromIrctc, fetchNearbyStationsFromIrctc } from "../services/irctc.service";
import { ValidationError } from "../utils/errors";

export interface FindStationParams {
  /** Text query — station name, code, or city. Used when lat/lng are not provided. */
  query?: string;
  /** Latitude for nearby search. Must be paired with lng. */
  lat?: number;
  /** Longitude for nearby search. Must be paired with lat. */
  lng?: number;
  /** When true and query is provided, returns a single best-match { code, fullName }.
   *  When false (default) and query is provided, returns up to 10 matches with full details.
   *  Ignored when lat/lng are provided. */
  exactMatch?: boolean;
}

/**
 * Merged tool: replaces search_stations + find_station_code + get_nearby_stations.
 *
 * Branching logic:
 * - lat + lng provided     → nearby stations within 50km (get_nearby_stations behaviour)
 * - query + exactMatch=true → single best match with code+fullName (find_station_code behaviour)
 * - query only              → up to 10 partial matches (search_stations behaviour)
 */
export async function findStationTool(params: FindStationParams): Promise<object> {
  const { query, lat, lng, exactMatch = false } = params;

  if (lat !== undefined && lng !== undefined) {
    return fetchNearbyStationsFromIrctc(lat, lng);
  }

  if (query) {
    if (exactMatch) {
      return fetchStationCodeFromIrctc(query);
    }
    return fetchStationsFromIrctc(query);
  }

  throw new ValidationError("Provide either 'query' for text search or 'lat'+'lng' for nearby search.");
}
