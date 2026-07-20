import { prisma } from "../prisma";
import { upsertUser } from "../repositories/user.repository";
import { UserContext } from "../types";

export async function savedPassengersTool(user: UserContext) {
    const dbUser = await upsertUser(user.email, user.name);
    return prisma.passenger.findMany({ where: { userId: dbUser.id } });
}
