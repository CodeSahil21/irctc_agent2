import { fetchStationCodeFromIrctc } from "../services/irctc.service";

export async function findStationCodeTool(query: string): Promise<{ code: string; fullName: string }> {
  return fetchStationCodeFromIrctc(query);
}
