import { UserContext } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { getRemindersByUser } from "../services/reminder.service";

export async function getRemindersTool(user: UserContext) {
  const dbUser = await upsertUser(user.email, user.name);
  return getRemindersByUser(dbUser.id);
}
