import { UpdateBookingStatusParams } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { updateBookingStatus, getBookingByPnr } from "../repositories/booking.repository";
import { BookingStatus } from "@prisma/client";

export async function updateBookingStatusTool(params: UpdateBookingStatusParams) {
  const { user, pnr, status, transactionId } = params;
  const dbUser = await upsertUser(user.email, user.name);
  await updateBookingStatus(dbUser.id, pnr, status as BookingStatus, transactionId);
  return getBookingByPnr(dbUser.id, pnr);
}
