import { BookingStatus } from "@prisma/client";
import { prisma } from "../prisma";
import { NotFoundError } from "../utils/errors";

export async function getBookingsByUser(userId: string) {
    return prisma.booking.findMany({
        where: { userId },
        include: { passengers: true },
    });
}

export async function getBookingByPnr(userId: string, pnr: string) {
    const booking = await prisma.booking.findFirst({
        where: { pnr, userId },
        include: { passengers: true },
    });
    if (!booking) throw new NotFoundError("Booking", pnr);
    return booking;
}

export async function updateBookingPnr(bookingId: string, pnr: string) {
    return prisma.booking.update({ where: { id: bookingId }, data: { pnr } });
}

export async function updateBookingStatus(
    userId: string,
    pnr: string,
    status: BookingStatus,
    transactionId?: string,
) {
    const now = new Date();
    return prisma.booking.updateMany({
        where: { pnr, userId },
        data: {
            status,
            ...(transactionId && { transactionId }),
            ...(status === BookingStatus.BOOKED && { bookedAt: now }),
            ...(status === BookingStatus.CANCELLED && { cancelledAt: now }),
        },
    });
}

export async function updateBoardingPoint(
    userId: string,
    pnr: string,
    newBoardingStation: string,
) {
    const booking = await prisma.booking.findFirst({ where: { pnr, userId } });
    if (!booking) throw new NotFoundError("Booking", pnr);

    return prisma.booking.update({
        where: { id: booking.id },
        data: { source: newBoardingStation },
    });
}
