import { prisma } from "../prisma";
import { upsertUser } from "../repositories/user.repository";
import { createBooking } from "../services/booking.service";
import { BookTicketParams } from "../types";

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
    } = params;

    const dbUser = await upsertUser(user.email, user.name);

    const booking = await createBooking({
        userId: dbUser.id,
        trainNumber,
        trainName,
        source,
        destination,
        journeyDate: new Date(journeyDate),
        travelClass,
        quota,
        fare,
        passengerCount: passengers.length,
    });

    // Assign deterministic coach/seat to each passenger
    await prisma.bookingPassenger.createMany({
        data: passengers.map((p, i) => ({
            bookingId: booking.id,
            name: p.name,
            age: p.age,
            gender: p.gender,
            berthPreference: p.berthPreference ?? null,
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
