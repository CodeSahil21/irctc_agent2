import { AvailableBoardingPointsParams } from "../types";
import { fetchBoardingPointsFromIrctc } from "../services/irctc.service";

export async function availableBoardingPointsTool(params: AvailableBoardingPointsParams): Promise<object> {
  const { trainNumber, fromStation, journeyDate } = params;
  return fetchBoardingPointsFromIrctc(trainNumber, fromStation, journeyDate);
}
