import { UpdateBoardingPointParams } from "../types";
import { upsertUser } from "../repositories/user.repository";
import { updateBoardingPoint } from "../repositories/booking.repository";

// Boarding point can only be changed by the user who owns the booking.
// updateBoardingPoint verifies userId + pnr match before updating.
export async function updateBoardingPointTool(params: UpdateBoardingPointParams) {
  const { user, pnr, newBoardingStation } = params;
  const dbUser = await upsertUser(user.email, user.name);

  return updateBoardingPoint(dbUser.id, pnr, newBoardingStation);
}
