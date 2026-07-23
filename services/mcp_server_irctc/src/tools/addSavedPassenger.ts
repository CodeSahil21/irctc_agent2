import { prisma } from "../prisma";
import { upsertUser } from "../repositories/user.repository";
import { AddSavedPassengerParams } from "../types";
import { ValidationError } from "../utils/errors";

// Valid IRCTC berth preference codes
const VALID_BERTH_PREFS = new Set(["LB", "MB", "UB", "SL", "SUB", "WS"]);

function normalizeBerthPreference(value?: string): string | null {
    if (!value) return null;
    const upper = value.toUpperCase().trim();
    // Accept common verbose aliases and map them to codes
    const aliases: Record<string, string> = {
        LOWER: "LB",
        MIDDLE: "MB",
        UPPER: "UB",
        "SIDE LOWER": "SL",
        "SIDE UPPER": "SUB",
        SU: "SUB",       // docs list "SU" — accept it as alias for SUB
        "WINDOW SEAT": "WS",
    };
    const normalized = aliases[upper] ?? upper;
    if (!VALID_BERTH_PREFS.has(normalized)) {
        throw new ValidationError(
            `Invalid berthPreference "${value}". Valid values: LB, MB, UB, SL, SUB (or SU), WS.`,
        );
    }
    return normalized;
}

export async function addSavedPassengerTool(params: AddSavedPassengerParams) {
    const { user, name, age, gender, berthPreference, seniorCitizen } = params;
    const dbUser = await upsertUser(user.email, user.name);

    return prisma.passenger.create({
        data: {
            userId: dbUser.id,
            name,
            age,
            gender,
            berthPreference: normalizeBerthPreference(berthPreference),
            seniorCitizen: seniorCitizen ?? false,
        },
    });
}
