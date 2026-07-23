import { TrainSearchParams } from "../types";
import { getTrainSearchCache, setTrainSearchCache } from "../services/cache.service";
import { fetchTrainsFromIrctc } from "../services/irctc.service";
import { ValidationError } from "../utils/errors";

export async function searchTrainsTool(params: TrainSearchParams) {
  const { fromStation, toStation, journeyDate, quota } = params;
  const date = new Date(journeyDate);
  if (isNaN(date.getTime())) {
    throw new ValidationError(`Invalid journeyDate: "${journeyDate}". Expected format YYYY-MM-DD.`);
  }

  const cached = await getTrainSearchCache(fromStation, toStation, date);
  if (cached) return cached;

  const result = await fetchTrainsFromIrctc(fromStation, toStation, journeyDate, quota);
  await setTrainSearchCache(fromStation, toStation, date, result);
  return result;
}
