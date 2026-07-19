// ── User context (only for user-specific tools) ──

export interface UserContext {
  email: string;
  name?: string;
}

// ── Public tool params ──

export interface TrainSearchParams {
  fromStation: string;
  toStation: string;
  journeyDate: string;
  quota?: string;
}

export interface CheckAvailabilityParams {
  trainNumber: string;
  travelClass: string;
  quota: string;
  journeyDate: string;
}

export interface FareParams {
  trainNumber: string;
  travelClass: string;
  quota: string;
  fromStation: string;
  toStation: string;
}

export interface RecommendTrainsParams {
  fromStation: string;
  toStation: string;
  journeyDate: string;
  preference: "fastest" | "cheapest" | "overnight";
  travelClass?: string;
  quota?: string;
}

export interface GetRouteParams {
  trainNumber: string;
}

export interface SeatMapParams {
  trainNumber: string;
  travelClass: string;
  journeyDate: string;
}

export interface AvailableBoardingPointsParams {
  trainNumber: string;
  fromStation: string;
  journeyDate: string;
}

// ── User-specific tool params ──

export interface PassengerInput {
  name: string;
  age: number;
  gender: "MALE" | "FEMALE" | "OTHER";
  berthPreference?: string;
}

export interface BookTicketParams {
  user: UserContext;
  trainNumber: string;
  trainName: string;
  source: string;
  destination: string;
  journeyDate: string;
  travelClass: string;
  quota: string;
  fare: number;
  passengers: PassengerInput[];
}

export interface CancelTicketParams {
  user: UserContext;
  pnr: string;
}

export interface PnrParams {
  user: UserContext;
  pnr: string;
}

export interface GetBookingParams {
  user: UserContext;
  pnr: string;
}

export interface ReminderParams {
  user: UserContext;
  type: "JOURNEY" | "PNR" | "BOOKING";
  reminderAt: string;
  bookingId?: string;
  metadata?: object;
}

export interface UpdateReminderParams {
  user: UserContext;
  reminderId: string;
  reminderAt?: string;
  type?: "JOURNEY" | "PNR" | "BOOKING";
  metadata?: object;
}

export interface DeleteReminderParams {
  user: UserContext;
  reminderId: string;
}

export interface AddSavedPassengerParams {
  user: UserContext;
  name: string;
  age: number;
  gender: "MALE" | "FEMALE" | "OTHER";
  berthPreference?: string;
  seniorCitizen?: boolean;
}

export interface UpdateBookingStatusParams {
  user: UserContext;
  pnr: string;
  status: "PENDING" | "BOOKED" | "RAC" | "WL" | "CANCELLED" | "FAILED";
  transactionId?: string;
}

export interface UpdateBoardingPointParams {
  user: UserContext;
  pnr: string;
  newBoardingStation: string;
}
