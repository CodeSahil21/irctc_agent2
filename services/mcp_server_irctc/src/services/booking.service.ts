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
    idempotencyKey?: string;
}) {
    // Retry on PNR collision (unique constraint); up to 5 attempts before giving up
    const MAX_ATTEMPTS = 5;
    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
        try {
            return await prisma.booking.create({
                data: {
                    ...data,
                    pnr: generatePnr(),
                    status: BookingStatus.BOOKED,
                    bookedAt: new Date(),
                },
            });
        } catch (err: any) {
            const isUniqueViolation =
                err?.code === "P2002" &&
                (err?.meta?.target as string[] | undefined)?.includes("pnr");
            if (!isUniqueViolation || attempt === MAX_ATTEMPTS) throw err;
            // else: retry with a freshly generated PNR
        }
    }
    // TypeScript requires an explicit unreachable return; the loop always throws or returns
    throw new Error("Unreachable");
}
