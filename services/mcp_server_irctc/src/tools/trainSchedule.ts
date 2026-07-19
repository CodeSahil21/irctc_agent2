import { fetchTrainScheduleFromIrctc } from "../services/irctc.service";

export async function trainScheduleTool(trainNumber: string): Promise<object> {
  return fetchTrainScheduleFromIrctc(trainNumber);
}
