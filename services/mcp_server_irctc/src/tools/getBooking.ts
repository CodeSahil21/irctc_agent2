import { GetBookingParams } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { getBookingByPnr } from "../repositories/booking.repository";

export async function getBookingTool(params: GetBookingParams) {
  const { user, pnr } = params;
  const dbUser = await upsertUser(user.email, user.name);
  return getBookingByPnr(dbUser.id, pnr);
}
