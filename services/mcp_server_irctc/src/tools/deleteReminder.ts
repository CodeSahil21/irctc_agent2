import { DeleteReminderParams } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { deleteReminder } from "../services/reminder.service";

export async function deleteReminderTool(params: DeleteReminderParams) {
  const { user, reminderId } = params;
  const dbUser = await upsertUser(user.email, user.name);
  return deleteReminder(dbUser.id, reminderId);
}
