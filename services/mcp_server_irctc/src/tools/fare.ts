import { FareParams } from "../types";
import { getFareCache, setFareCache } from "../services/cache.service";
import { fetchFareFromIrctc } from "../services/irctc.service";

export async function fareTool(params: FareParams) {
  const { trainNumber, travelClass, quota, fromStation, toStation } = params;

  const cached = await getFareCache(trainNumber, travelClass, quota, fromStation, toStation);
  if (cached) return cached;

  const result = await fetchFareFromIrctc(trainNumber, travelClass, quota, fromStation, toStation);
  await setFareCache(trainNumber, travelClass, quota, fromStation, toStation, result);
  return result;
}
