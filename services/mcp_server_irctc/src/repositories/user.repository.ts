import { prisma } from "../prisma";

export async function upsertUser(email: string, name?: string) {
    return prisma.user.upsert({
        where: { email },
        update: { name },
        create: { email, name },
    });
}

export async function getUserByEmail(email: string) {
    return prisma.user.findUnique({ where: { email } });
}
