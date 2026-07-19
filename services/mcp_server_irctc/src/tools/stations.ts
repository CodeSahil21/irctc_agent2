import { fetchStationsFromIrctc } from "../services/irctc.service";

export async function stationsTool(query: string): Promise<object> {
  return fetchStationsFromIrctc(query);
}
