import { UserContext } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { getBookingsByUser } from "../repositories/booking.repository";

export async function bookingHistoryTool(user: UserContext) {
  const dbUser = await upsertUser(user.email, user.name);
  return getBookingsByUser(dbUser.id);
}
