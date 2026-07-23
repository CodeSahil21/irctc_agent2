import { BookingStatus } from "@prisma/client";
import { prisma } from "../prisma";
import { UserContext } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { ValidationError, NotFoundError } from "../utils/errors";

export interface UpdateBookingParams {
  user: UserContext;
  pnr: string;
  /** New booking status — required if updating status */
  status?: "PENDING" | "BOOKED" | "RAC" | "WL" | "CANCELLED" | "FAILED";
  /** Payment transaction ID — only used when updating status */
  transactionId?: string;
  /** New boarding station code — required if changing boarding point */
  newBoardingStation?: string;
}

/**
 * Merged tool: replaces update_booking_status + update_boarding_point.
 * At least one of `status` or `newBoardingStation` must be provided.
 * Both ops run inside a single transaction — if either fails the whole update rolls back.
 */
export async function updateBookingTool(params: UpdateBookingParams) {
  const { user, pnr, status, transactionId, newBoardingStation } = params;

  if (!status && !newBoardingStation) {
    throw new ValidationError("At least one of 'status' or 'newBoardingStation' must be provided.");
  }

  const dbUser = await upsertUser(user.email, user.name);

  // Resolve booking id once outside the transaction (read-only, no atomicity needed)
  const booking = await prisma.booking.findFirst({ where: { pnr, userId: dbUser.id } });
  if (!booking) throw new NotFoundError("Booking", pnr);

  await prisma.$transaction(async (tx) => {
    if (status) {
      const now = new Date();
      await tx.booking.updateMany({
        where: { pnr, userId: dbUser.id },
        data: {
          status: status as BookingStatus,
          ...(transactionId && { transactionId }),
          ...(status === "BOOKED" && { bookedAt: now }),
          ...(status === "CANCELLED" && { cancelledAt: now }),
        },
      });
    }

    if (newBoardingStation) {
      await tx.booking.update({
        where: { id: booking.id },
        data: { source: newBoardingStation },
      });
    }
  });

  // Return the final state after both updates
  return prisma.booking.findUnique({
    where: { id: booking.id },
    include: { passengers: true },
  });
}
