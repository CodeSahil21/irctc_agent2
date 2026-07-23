import { CheckAvailabilityParams } from "../types";
import { getAvailabilityCache, setAvailabilityCache } from "../services/cache.service";
import { fetchAvailabilityFromIrctc } from "../services/irctc.service";
import { ValidationError } from "../utils/errors";

export async function checkAvailabilityTool(params: CheckAvailabilityParams) {
  const { trainNumber, travelClass, quota, journeyDate } = params;
  const date = new Date(journeyDate);
  if (isNaN(date.getTime())) {
    throw new ValidationError(`Invalid journeyDate: "${journeyDate}". Expected format YYYY-MM-DD.`);
  }

  const cached = await getAvailabilityCache(trainNumber, travelClass, quota, date);
  if (cached) return cached;

  const result = await fetchAvailabilityFromIrctc(trainNumber, travelClass, quota, journeyDate);
  await setAvailabilityCache(trainNumber, travelClass, quota, date, result);
  return result;
}
