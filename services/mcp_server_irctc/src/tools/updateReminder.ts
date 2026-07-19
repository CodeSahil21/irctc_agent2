import { UpdateReminderParams } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { updateReminder } from "../services/reminder.service";
import { ReminderType } from "@prisma/client";

export async function updateReminderTool(params: UpdateReminderParams) {
  const { user, reminderId, reminderAt, type, metadata } = params;
  const dbUser = await upsertUser(user.email, user.name);

  return updateReminder(dbUser.id, reminderId, {
    ...(reminderAt && { reminderAt: new Date(reminderAt) }),
    ...(type && { type: type as ReminderType }),
    ...(metadata && { metadata }),
  });
}
