import { fetchTrainByNumberFromIrctc, fetchTrainRouteFromIrctc, fetchTrainScheduleFromIrctc } from "../services/irctc.service";
import { IrctcError } from "../utils/errors";

export interface GetTrainDetailsParams {
  trainNumber: string;
  include?: Array<"info" | "route" | "schedule">;
}

/**
 * Merged tool: replaces search_train_by_number + get_route + get_train_schedule.
 * `include` defaults to ["info"] — pass additional values to get route/schedule too.
 * e.g. include: ["info","route","schedule"] returns everything in one call.
 */
export async function getTrainDetailsTool(params: GetTrainDetailsParams): Promise<object> {
  const { trainNumber, include = ["info"] } = params;
  const result: Record<string, unknown> = {};

  await Promise.all(
    include.map(async (section) => {
      switch (section) {
        case "info":
          result.info = await fetchTrainByNumberFromIrctc(trainNumber);
          break;
        case "route":
          result.route = await fetchTrainRouteFromIrctc(trainNumber);
          break;
        case "schedule":
          result.schedule = await fetchTrainScheduleFromIrctc(trainNumber);
          break;
        default:
          throw new IrctcError(`Unknown include value: ${section}`);
      }
    })
  );

  return result;
}
