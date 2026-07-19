import { PnrParams } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { upsertPnrTracking } from "../services/pnr.service";

export async function getPnrTool(params: PnrParams) {
  const { user, pnr } = params;
  const dbUser = await upsertUser(user.email, user.name);
  return upsertPnrTracking(dbUser.id, pnr, {});
}
