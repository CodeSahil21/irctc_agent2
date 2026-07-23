import { UserContext } from "../types";
import { upsertUser } from "../repositories/user.repository";
import {
  createReminder,
  getRemindersByUser,
  updateReminder,
  deleteReminder,
} from "../services/reminder.service";
import { ReminderType } from "@prisma/client";
import { ValidationError } from "../utils/errors";

export interface ManageReminderParams {
  user: UserContext;
  action: "create" | "update" | "delete" | "list";
  // create
  type?: "JOURNEY" | "PNR" | "BOOKING";
  reminderAt?: string;
  bookingId?: string;
  metadata?: object;
  // update / delete
  reminderId?: string;
}

/**
 * Merged tool: replaces create_reminder + get_reminders + update_reminder + delete_reminder.
 *
 * action="create"  → requires type, reminderAt. Optional: bookingId, metadata.
 * action="list"    → no extra params needed.
 * action="update"  → requires reminderId. Optional: reminderAt, type, metadata.
 * action="delete"  → requires reminderId.
 */
export async function manageReminderTool(params: ManageReminderParams) {
  const { user, action, type, reminderAt, bookingId, metadata, reminderId } = params;
  const dbUser = await upsertUser(user.email, user.name);

  switch (action) {
    case "create": {
      if (!type) throw new ValidationError("'type' is required for action='create'.");
      if (!reminderAt) throw new ValidationError("'reminderAt' is required for action='create'.");
      return createReminder(dbUser.id, type as ReminderType, new Date(reminderAt), bookingId, metadata);
    }

    case "list": {
      return getRemindersByUser(dbUser.id);
    }

    case "update": {
      if (!reminderId) throw new ValidationError("'reminderId' is required for action='update'.");
      return updateReminder(dbUser.id, reminderId, {
        ...(reminderAt && { reminderAt: new Date(reminderAt) }),
        ...(type && { type: type as ReminderType }),
        ...(metadata && { metadata }),
      });
    }

    case "delete": {
      if (!reminderId) throw new ValidationError("'reminderId' is required for action='delete'.");
      return deleteReminder(dbUser.id, reminderId);
    }

    default:
      throw new ValidationError(`Unknown action: ${(params as any).action}. Valid: create, list, update, delete.`);
  }
}
