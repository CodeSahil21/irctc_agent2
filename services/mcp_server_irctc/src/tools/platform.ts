import { fetchPlatformFromIrctc } from "../services/irctc.service";

export async function platformTool(trainNumber: string, stationCode: string): Promise<object> {
  return fetchPlatformFromIrctc(trainNumber, stationCode);
}
