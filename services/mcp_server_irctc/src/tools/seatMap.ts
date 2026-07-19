import { SeatMapParams } from "../types";
import { fetchSeatMapFromIrctc } from "../services/irctc.service";

export async function seatMapTool(params: SeatMapParams): Promise<object> {
  const { trainNumber, travelClass, journeyDate } = params;
  return fetchSeatMapFromIrctc(trainNumber, travelClass, journeyDate);
}
