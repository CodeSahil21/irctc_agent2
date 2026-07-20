import { prisma } from "../prisma";

export async function findUserByEmail(email: string) {
    return prisma.user.findUnique({ where: { email } });
}

export async function findUserById(id: string) {
    return prisma.user.findUnique({ where: { id } });
}

export async function createUser(
    email: string,
    name: string | undefined,
    passwordHash: string,
) {
    return prisma.user.create({ data: { email, name, passwordHash } });
}

export async function saveRefreshToken(
    userId: string,
    tokenHash: string,
    expiresAt: Date,
) {
    return prisma.refreshToken.create({
        data: { userId, tokenHash, expiresAt },
    });
}

export async function findRefreshToken(tokenHash: string) {
    return prisma.refreshToken.findUnique({
        where: { tokenHash },
    });
}

export async function deleteRefreshToken(tokenHash: string) {
    return prisma.refreshToken.deleteMany({ where: { tokenHash } });
}

export async function deleteAllRefreshTokensForUser(userId: string) {
    return prisma.refreshToken.deleteMany({ where: { userId } });
}

export async function deleteExpiredRefreshTokens() {
    return prisma.refreshToken.deleteMany({
        where: { expiresAt: { lt: new Date() } },
    });
}
