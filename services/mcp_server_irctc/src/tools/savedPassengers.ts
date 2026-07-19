import { UserContext } from "../types";
import { upsertUser } from "../repositories/user.repository";
import prisma from "../prisma";

export async function savedPassengersTool(user: UserContext) {
  const dbUser = await upsertUser(user.email, user.name);
  return prisma.passenger.findMany({ where: { userId: dbUser.id } });
}
