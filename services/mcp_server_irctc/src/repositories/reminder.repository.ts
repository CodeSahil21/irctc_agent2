import { prisma } from "../prisma";

export async function markReminderSent(id: string) {
    return prisma.reminder.update({ where: { id }, data: { sent: true } });
}
