import { prisma } from "../prisma";
import { upsertUser } from "../repositories/user.repository";
import { createBooking } from "../services/booking.service";
import { BookTicketParams } from "../types";
import { ValidationError } from "../utils/errors";

// Valid IRCTC berth preference codes (mirrors addSavedPassenger.ts)
const VALID_BERTH_PREFS = new Set(["LB", "MB", "UB", "SL", "SUB", "WS"]);

function normalizeBerthPreference(value?: string): string | null {
    if (!value) return null;
    const upper = value.toUpperCase().trim();
    const aliases: Record<string, string> = {
        LOWER: "LB",
        MIDDLE: "MB",
        UPPER: "UB",
        "SIDE LOWER": "SL",
        "SIDE UPPER": "SUB",
        SU: "SUB",       // docs list "SU" — accept it as alias for SUB
        "WINDOW SEAT": "WS",
    };
    const normalized = aliases[upper] ?? upper;
    if (!VALID_BERTH_PREFS.has(normalized)) {
        throw new ValidationError(
            `Invalid berthPreference "${value}". Valid values: LB, MB, UB, SL, SUB (or SU), WS.`,
        );
    }
    return normalized;
}

export async function bookTicketTool(params: BookTicketParams) {
    const {
        user,
        passengers,
        journeyDate,
        fare,
        trainNumber,
        trainName,
        source,
        destination,
        travelClass,
        quota,
        idempotencyKey,
    } = params;

    const parsedDate = new Date(journeyDate);
    if (isNaN(parsedDate.getTime())) {
        throw new ValidationError(`Invalid journeyDate: "${journeyDate}". Expected format YYYY-MM-DD.`);
    }

    const dbUser = await upsertUser(user.email, user.name);

    // Idempotency: if a booking with this key already exists for this user, return it
    // rather than creating a duplicate. Protects against agent retries on timeout.
    if (idempotencyKey) {
        const existing = await prisma.booking.findFirst({
            where: { userId: dbUser.id, idempotencyKey },
            include: { passengers: true },
        });
        if (existing) {
            return {
                pnr: existing.pnr,
                status: existing.status,
                bookedAt: existing.bookedAt,
                trainNumber: existing.trainNumber,
                trainName: existing.trainName,
                source: existing.source,
                destination: existing.destination,
                journeyDate: existing.journeyDate,
                travelClass: existing.travelClass,
                quota: existing.quota,
                fare: existing.fare,
                passengerCount: existing.passengerCount,
                idempotencyKey: existing.idempotencyKey,
                alreadyBooked: true,
                passengers: existing.passengers.map((p) => ({
                    name: p.name,
                    age: p.age,
                    gender: p.gender,
                    berthPreference: p.berthPreference,
                    coach: p.coach,
                    seat: p.seat,
                    currentStatus: p.currentStatus,
                    finalStatus: p.finalStatus,
                })),
            };
        }
    }

    const booking = await createBooking({
        userId: dbUser.id,
        trainNumber,
        trainName,
        source,
        destination,
        journeyDate: parsedDate,
        travelClass,
        quota,
        fare,
        passengerCount: passengers.length,
        idempotencyKey,
    });

    // Assign deterministic coach/seat to each passenger
    await prisma.bookingPassenger.createMany({
        data: passengers.map((p, i) => ({
            bookingId: booking.id,
            name: p.name,
            age: p.age,
            gender: p.gender,
            berthPreference: normalizeBerthPreference(p.berthPreference),
            coach: `${travelClass}1`,
            seat: String(i + 1),
            currentStatus: "CNF",
            finalStatus: "CNF",
        })),
    });

    const result = await prisma.booking.findUnique({
        where: { id: booking.id },
        include: { passengers: true },
    });

    return {
        pnr: result!.pnr,
        status: result!.status,
        bookedAt: result!.bookedAt,
        trainNumber: result!.trainNumber,
        trainName: result!.trainName,
        source: result!.source,
        destination: result!.destination,
        journeyDate: result!.journeyDate,
        travelClass: result!.travelClass,
        quota: result!.quota,
        fare: result!.fare,
        passengerCount: result!.passengerCount,
        idempotencyKey: result!.idempotencyKey,
        alreadyBooked: false,
        passengers: result!.passengers.map((p) => ({
            name: p.name,
            age: p.age,
            gender: p.gender,
            berthPreference: p.berthPreference,
            coach: p.coach,
            seat: p.seat,
            currentStatus: p.currentStatus,
            finalStatus: p.finalStatus,
        })),
    };
}
