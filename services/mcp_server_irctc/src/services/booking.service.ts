import { BookingStatus } from "@prisma/client";
import { prisma } from "../prisma";

function generatePnr(): string {
    // PNR format: 10-digit numeric string like real IRCTC PNRs
    return Math.floor(1000000000 + Math.random() * 9000000000).toString();
}

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
        data: {
            ...data,
            pnr: generatePnr(),
            status: BookingStatus.BOOKED,
            bookedAt: new Date(),
        },
    });
}
