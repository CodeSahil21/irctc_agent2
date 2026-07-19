import prisma from "../prisma";

export async function saveSession(userId: string, irctcUsername: string, sessionToken: string, expiresAt?: Date) {
  return prisma.irctcSession.create({
    data: { userId, irctcUsername, cookies: { token: sessionToken }, expiresAt },
  });
}

export async function getActiveSession(userId: string) {
  return prisma.irctcSession.findFirst({ where: { userId, isLoggedIn: true } });
}

export async function invalidateSession(userId: string) {
  return prisma.irctcSession.updateMany({ where: { userId }, data: { isLoggedIn: false } });
}
