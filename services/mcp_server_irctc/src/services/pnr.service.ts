import prisma from "../prisma";

export async function upsertPnrTracking(userId: string, pnr: string, status: object) {
  return prisma.pnrTracking.upsert({
    where: { userId_pnr: { userId, pnr } },
    update: { lastStatus: status, checkedAt: new Date() },
    create: { userId, pnr, lastStatus: status, checkedAt: new Date() },
  });
}
