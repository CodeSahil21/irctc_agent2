-- CreateEnum
CREATE TYPE "Gender" AS ENUM ('MALE', 'FEMALE', 'OTHER');

-- CreateEnum
CREATE TYPE "BookingStatus" AS ENUM ('PENDING', 'BOOKED', 'RAC', 'WL', 'CANCELLED', 'FAILED');

-- CreateEnum
CREATE TYPE "ReminderType" AS ENUM ('JOURNEY', 'PNR', 'BOOKING');

-- CreateTable
CREATE TABLE "User" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "name" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "IrctcSession" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "irctcUsername" TEXT NOT NULL,
    "cookies" JSONB NOT NULL,
    "localStorage" JSONB,
    "sessionStorage" JSONB,
    "expiresAt" TIMESTAMP(3),
    "isLoggedIn" BOOLEAN NOT NULL DEFAULT true,
    "lastUsedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "deviceFingerprint" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "IrctcSession_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Booking" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "pnr" TEXT,
    "transactionId" TEXT,
    "trainNumber" TEXT NOT NULL,
    "trainName" TEXT NOT NULL,
    "source" TEXT NOT NULL,
    "destination" TEXT NOT NULL,
    "journeyDate" TIMESTAMP(3) NOT NULL,
    "travelClass" TEXT NOT NULL,
    "quota" TEXT NOT NULL,
    "status" "BookingStatus" NOT NULL,
    "fare" DECIMAL(10,2) NOT NULL,
    "passengerCount" INTEGER NOT NULL,
    "bookedAt" TIMESTAMP(3),
    "cancelledAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Booking_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "BookingPassenger" (
    "id" TEXT NOT NULL,
    "bookingId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "age" INTEGER NOT NULL,
    "gender" "Gender" NOT NULL,
    "berthPreference" TEXT,
    "coach" TEXT,
    "seat" TEXT,
    "currentStatus" TEXT,
    "finalStatus" TEXT,

    CONSTRAINT "BookingPassenger_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Passenger" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "age" INTEGER NOT NULL,
    "gender" "Gender" NOT NULL,
    "berthPreference" TEXT,
    "seniorCitizen" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "Passenger_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PnrTracking" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "pnr" TEXT NOT NULL,
    "lastStatus" JSONB NOT NULL,
    "checkedAt" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "PnrTracking_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Reminder" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "bookingId" TEXT,
    "type" "ReminderType" NOT NULL,
    "reminderAt" TIMESTAMP(3) NOT NULL,
    "sent" BOOLEAN NOT NULL DEFAULT false,
    "metadata" JSONB,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "Reminder_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Station" (
    "code" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "city" TEXT NOT NULL,
    "state" TEXT NOT NULL,
    "zone" TEXT NOT NULL,
    "lat" DOUBLE PRECISION,
    "lng" DOUBLE PRECISION,

    CONSTRAINT "Station_pkey" PRIMARY KEY ("code")
);

-- CreateTable
CREATE TABLE "Train" (
    "number" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "runsDays" TEXT NOT NULL,
    "classes" TEXT NOT NULL,
    "quotas" TEXT NOT NULL,

    CONSTRAINT "Train_pkey" PRIMARY KEY ("number")
);

-- CreateTable
CREATE TABLE "TrainScheduleStop" (
    "id" TEXT NOT NULL,
    "trainNumber" TEXT NOT NULL,
    "stationCode" TEXT NOT NULL,
    "stationName" TEXT NOT NULL,
    "arrivalTime" TEXT,
    "departureTime" TEXT,
    "dayOffset" INTEGER NOT NULL DEFAULT 0,
    "stopNumber" INTEGER NOT NULL,
    "distanceFromOrigin" INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT "TrainScheduleStop_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "TrainSearchCache" (
    "id" TEXT NOT NULL,
    "fromStation" TEXT NOT NULL,
    "toStation" TEXT NOT NULL,
    "journeyDate" TIMESTAMP(3) NOT NULL,
    "response" JSONB NOT NULL,
    "expiresAt" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "TrainSearchCache_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AvailabilityCache" (
    "id" TEXT NOT NULL,
    "trainNumber" TEXT NOT NULL,
    "travelClass" TEXT NOT NULL,
    "quota" TEXT NOT NULL,
    "journeyDate" TIMESTAMP(3) NOT NULL,
    "response" JSONB NOT NULL,
    "expiresAt" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "AvailabilityCache_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "FareCache" (
    "id" TEXT NOT NULL,
    "trainNumber" TEXT NOT NULL,
    "travelClass" TEXT NOT NULL,
    "quota" TEXT NOT NULL,
    "fromStation" TEXT NOT NULL,
    "toStation" TEXT NOT NULL,
    "response" JSONB NOT NULL,
    "expiresAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "FareCache_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ToolExecution" (
    "id" TEXT NOT NULL,
    "toolName" TEXT NOT NULL,
    "userId" TEXT,
    "requestId" TEXT,
    "sessionId" TEXT,
    "input" JSONB NOT NULL,
    "output" JSONB,
    "success" BOOLEAN NOT NULL,
    "statusCode" INTEGER,
    "error" TEXT,
    "durationMs" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ToolExecution_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE INDEX "IrctcSession_userId_idx" ON "IrctcSession"("userId");

-- CreateIndex
CREATE INDEX "IrctcSession_irctcUsername_idx" ON "IrctcSession"("irctcUsername");

-- CreateIndex
CREATE UNIQUE INDEX "Booking_pnr_key" ON "Booking"("pnr");

-- CreateIndex
CREATE INDEX "Booking_userId_idx" ON "Booking"("userId");

-- CreateIndex
CREATE INDEX "Booking_pnr_idx" ON "Booking"("pnr");

-- CreateIndex
CREATE INDEX "Booking_journeyDate_idx" ON "Booking"("journeyDate");

-- CreateIndex
CREATE INDEX "BookingPassenger_bookingId_idx" ON "BookingPassenger"("bookingId");

-- CreateIndex
CREATE INDEX "Passenger_userId_idx" ON "Passenger"("userId");

-- CreateIndex
CREATE INDEX "PnrTracking_userId_idx" ON "PnrTracking"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "PnrTracking_userId_pnr_key" ON "PnrTracking"("userId", "pnr");

-- CreateIndex
CREATE INDEX "Reminder_userId_idx" ON "Reminder"("userId");

-- CreateIndex
CREATE INDEX "Reminder_bookingId_idx" ON "Reminder"("bookingId");

-- CreateIndex
CREATE INDEX "TrainScheduleStop_trainNumber_idx" ON "TrainScheduleStop"("trainNumber");

-- CreateIndex
CREATE INDEX "TrainScheduleStop_stationCode_idx" ON "TrainScheduleStop"("stationCode");

-- CreateIndex
CREATE UNIQUE INDEX "TrainScheduleStop_trainNumber_stationCode_key" ON "TrainScheduleStop"("trainNumber", "stationCode");

-- CreateIndex
CREATE UNIQUE INDEX "TrainSearchCache_fromStation_toStation_journeyDate_key" ON "TrainSearchCache"("fromStation", "toStation", "journeyDate");

-- CreateIndex
CREATE UNIQUE INDEX "AvailabilityCache_trainNumber_travelClass_quota_journeyDate_key" ON "AvailabilityCache"("trainNumber", "travelClass", "quota", "journeyDate");

-- CreateIndex
CREATE UNIQUE INDEX "FareCache_trainNumber_fromStation_toStation_travelClass_quo_key" ON "FareCache"("trainNumber", "fromStation", "toStation", "travelClass", "quota");

-- CreateIndex
CREATE INDEX "ToolExecution_toolName_idx" ON "ToolExecution"("toolName");

-- CreateIndex
CREATE INDEX "ToolExecution_userId_idx" ON "ToolExecution"("userId");

-- CreateIndex
CREATE INDEX "ToolExecution_createdAt_idx" ON "ToolExecution"("createdAt");

-- AddForeignKey
ALTER TABLE "IrctcSession" ADD CONSTRAINT "IrctcSession_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Booking" ADD CONSTRAINT "Booking_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "BookingPassenger" ADD CONSTRAINT "BookingPassenger_bookingId_fkey" FOREIGN KEY ("bookingId") REFERENCES "Booking"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Passenger" ADD CONSTRAINT "Passenger_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PnrTracking" ADD CONSTRAINT "PnrTracking_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Reminder" ADD CONSTRAINT "Reminder_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Reminder" ADD CONSTRAINT "Reminder_bookingId_fkey" FOREIGN KEY ("bookingId") REFERENCES "Booking"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TrainScheduleStop" ADD CONSTRAINT "TrainScheduleStop_trainNumber_fkey" FOREIGN KEY ("trainNumber") REFERENCES "Train"("number") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "TrainScheduleStop" ADD CONSTRAINT "TrainScheduleStop_stationCode_fkey" FOREIGN KEY ("stationCode") REFERENCES "Station"("code") ON DELETE CASCADE ON UPDATE CASCADE;
