import { RecommendTrainsParams } from "../types";
import { searchTrainsTool } from "./searchTrains";
import { checkAvailabilityTool } from "./checkAvailability";
import { fareTool } from "./fare";

export async function recommendTrainsTool(params: RecommendTrainsParams): Promise<object> {
  const { fromStation, toStation, journeyDate, preference, travelClass = "SL", quota = "GN" } = params;

  const trains = await searchTrainsTool({ fromStation, toStation, journeyDate, quota }) as any[];
  if (!trains || trains.length === 0) return { trains: [] };

  const enriched = await Promise.all(
    trains.map(async (train: any) => {
      const [availability, fare] = await Promise.all([
        checkAvailabilityTool({ trainNumber: train.trainNumber, travelClass, quota, journeyDate }),
        fareTool({ trainNumber: train.trainNumber, travelClass, quota, fromStation, toStation }),
      ]);
      return { ...train, availability, fare };
    })
  );

  const sorted = enriched.sort((a, b) => {
    if (preference === "cheapest") return (a.fare as any)?.amount - (b.fare as any)?.amount;
    if (preference === "fastest") return (a.durationMins as number) - (b.durationMins as number);
    if (preference === "overnight") {
      const hour = (t: any) => parseInt(t.departure?.split(":")[0] ?? "12");
      return hour(b) >= 18 ? 1 : hour(a) >= 18 ? -1 : 0;
    }
    return 0;
  });

  return { trains: sorted.slice(0, 5) };
}
