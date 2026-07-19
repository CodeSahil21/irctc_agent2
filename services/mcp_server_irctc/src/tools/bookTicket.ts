import { BookTicketParams } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { createBooking } from "../services/booking.service";
import prisma from "../prisma";

export async function bookTicketTool(params: BookTicketParams) {
  const { user, passengers, journeyDate, fare, trainNumber, trainName, source, destination, travelClass, quota } = params;
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

  await prisma.bookingPassenger.createMany({
    data: passengers.map((p) => ({
      bookingId: booking.id,
      name: p.name,
      age: p.age,
      gender: p.gender,
      berthPreference: p.berthPreference,
    })),
  });

  return prisma.booking.findUnique({
    where: { id: booking.id },
    include: { passengers: true },
  });
}
