import { fetchLiveStatusFromIrctc } from "../services/irctc.service";

export async function liveStatusTool(trainNumber: string, date: string): Promise<object> {
  return fetchLiveStatusFromIrctc(trainNumber, date);
}
