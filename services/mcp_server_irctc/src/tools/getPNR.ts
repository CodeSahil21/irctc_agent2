import { PnrParams } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { getBookingByPnr } from "../repositories/booking.repository";
import { upsertPnrTracking } from "../services/pnr.service";

export async function getPnrTool(params: PnrParams) {
  const { user, pnr } = params;
  const dbUser = await upsertUser(user.email, user.name);
  const booking = await getBookingByPnr(dbUser.id, pnr);

  const status = {
    pnr: booking.pnr,
    status: booking.status,
    trainNumber: booking.trainNumber,
    trainName: booking.trainName,
    source: booking.source,
    destination: booking.destination,
    journeyDate: booking.journeyDate,
    travelClass: booking.travelClass,
    passengers: booking.passengers.map((p) => ({
      name: p.name,
      coach: p.coach,
      seat: p.seat,
      currentStatus: p.currentStatus,
    })),
  };

  await upsertPnrTracking(dbUser.id, pnr, status);
  return status;
}
