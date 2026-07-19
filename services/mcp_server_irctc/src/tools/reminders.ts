import { ReminderParams } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { createReminder } from "../services/reminder.service";
import { ReminderType } from "@prisma/client";

export async function remindersTool(params: ReminderParams) {
  const { user, type, reminderAt, bookingId, metadata } = params;
  const dbUser = await upsertUser(user.email, user.name);
  return createReminder(dbUser.id, type as ReminderType, new Date(reminderAt), bookingId, metadata);
}
