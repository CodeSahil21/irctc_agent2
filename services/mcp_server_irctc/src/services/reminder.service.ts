import prisma from "../prisma";
import { ReminderType } from "@prisma/client";
import { NotFoundError } from "../utils/errors";

export async function createReminder(userId: string, type: ReminderType, reminderAt: Date, bookingId?: string, metadata?: object) {
  return prisma.reminder.create({ data: { userId, type, reminderAt, bookingId, metadata } });
}

export async function getRemindersByUser(userId: string) {
  return prisma.reminder.findMany({ where: { userId }, orderBy: { reminderAt: "asc" } });
}

export async function updateReminder(userId: string, reminderId: string, data: { reminderAt?: Date; type?: ReminderType; metadata?: object }) {
  const reminder = await prisma.reminder.findFirst({ where: { id: reminderId, userId } });
  if (!reminder) throw new NotFoundError("Reminder", reminderId);
  return prisma.reminder.update({ where: { id: reminderId }, data });
}

export async function deleteReminder(userId: string, reminderId: string) {
  const reminder = await prisma.reminder.findFirst({ where: { id: reminderId, userId } });
  if (!reminder) throw new NotFoundError("Reminder", reminderId);
  return prisma.reminder.delete({ where: { id: reminderId } });
}

export async function getPendingReminders() {
  return prisma.reminder.findMany({ where: { sent: false, reminderAt: { lte: new Date() } } });
}
