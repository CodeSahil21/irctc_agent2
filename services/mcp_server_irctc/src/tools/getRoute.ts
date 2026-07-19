import { GetRouteParams } from "../types";
import { fetchTrainRouteFromIrctc } from "../services/irctc.service";

export async function getRouteTool(params: GetRouteParams): Promise<object> {
  return fetchTrainRouteFromIrctc(params.trainNumber);
}
