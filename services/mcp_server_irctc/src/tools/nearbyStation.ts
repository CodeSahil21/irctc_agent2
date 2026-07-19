import { fetchNearbyStationsFromIrctc } from "../services/irctc.service";

export async function nearbyStationTool(lat: number, lng: number): Promise<object> {
  return fetchNearbyStationsFromIrctc(lat, lng);
}
