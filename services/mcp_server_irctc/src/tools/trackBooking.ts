import { UserContext } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { getBookingByPnr } from "../repositories/booking.repository";
import { upsertPnrTracking } from "../services/pnr.service";

export interface TrackBookingParams {
  user: UserContext;
  pnr: string;
  /** When true (default), upserts a PnrTracking row and returns the tracking record.
   *  When false, returns the raw booking object only (no tracking upsert). */
  save?: boolean;
}

/**
 * Merged tool: replaces get_pnr + get_booking.
 * - save=true  → behaves like get_pnr: upserts tracking, returns { id, userId, pnr, lastStatus, checkedAt }
 * - save=false → behaves like get_booking: returns the full booking object directly
 */
export async function trackBookingTool(params: TrackBookingParams) {
  const { user, pnr, save = true } = params;
  const dbUser = await upsertUser(user.email, user.name);
  const booking = await getBookingByPnr(dbUser.id, pnr);

  if (!save) return booking;

  const lastStatus = {
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

  return upsertPnrTracking(dbUser.id, pnr, lastStatus);
}
