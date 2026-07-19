import { CancelTicketParams } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { updateBookingStatus } from "../repositories/booking.repository";
import { BookingStatus } from "@prisma/client";

export async function cancelTicketTool(params: CancelTicketParams) {
  const { user, pnr } = params;
  const dbUser = await upsertUser(user.email, user.name);
  return updateBookingStatus(dbUser.id, pnr, BookingStatus.CANCELLED);
}
