import { AddSavedPassengerParams } from "../types";
import { upsertUser } from "../repositories/user.repository";
import prisma from "../prisma";

export async function addSavedPassengerTool(params: AddSavedPassengerParams) {
  const { user, name, age, gender, berthPreference, seniorCitizen } = params;
  const dbUser = await upsertUser(user.email, user.name);

  return prisma.passenger.create({
    data: { userId: dbUser.id, name, age, gender, berthPreference, seniorCitizen: seniorCitizen ?? false },
  });
}
