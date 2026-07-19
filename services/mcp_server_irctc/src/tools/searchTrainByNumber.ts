import { fetchTrainByNumberFromIrctc } from "../services/irctc.service";

export async function searchTrainByNumberTool(trainNumber: string): Promise<object> {
  return fetchTrainByNumberFromIrctc(trainNumber);
}
