import { BookingStatus } from "@prisma/client";
import { prisma } from "../prisma";

export async function createBooking(data: {
    userId: string;
    trainNumber: string;
    trainName: string;
    source: string;
    destination: string;
    journeyDate: Date;
    travelClass: string;
    quota: string;
    fare: number;
    passengerCount: number;
}) {
    return prisma.booking.create({
        data: { ...data, status: BookingStatus.PENDING },
    });
}
