import { TrainSearchParams } from "../types";
import { getTrainSearchCache, setTrainSearchCache } from "../services/cache.service";
import { fetchTrainsFromIrctc } from "../services/irctc.service";

export async function searchTrainsTool(params: TrainSearchParams) {
  const { fromStation, toStation, journeyDate, quota } = params;
  const date = new Date(journeyDate);

  const cached = await getTrainSearchCache(fromStation, toStation, date);
  if (cached) return cached;

  const result = await fetchTrainsFromIrctc(fromStation, toStation, journeyDate, quota);
  await setTrainSearchCache(fromStation, toStation, date, result);
  return result;
}
