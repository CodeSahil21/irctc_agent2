import { prisma } from "../prisma";
import { IrctcError } from "../utils/errors";

// ── helpers ──────────────────────────────────────────────────────────────────

function parseTime(t: string): number {
    const [h, m] = t.split(":").map(Number);
    return h * 60 + m;
}

function minutesToHHMM(mins: number): string {
    const h = Math.floor(mins / 60) % 24;
    const m = mins % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function fareForClass(base: number, cls: string, quota: string): number {
    const classMultiplier: Record<string, number> = {
        SL: 1,
        "2S": 0.6,
        CC: 1.4,
        "3A": 2.2,
        "2A": 3.1,
        "1A": 5.0,
        EC: 3.5,
        VS: 2.8,
    };
    const quotaMultiplier: Record<string, number> = {
        GN: 1,
        LD: 1,
        SS: 0.5,
        TQ: 1.3,
        PT: 1.5,
        HO: 1,
    };
    return Math.round(
        base * (classMultiplier[cls] ?? 1) * (quotaMultiplier[quota] ?? 1),
    );
}

function availabilityStatus(trainNumber: string, cls: string, date: Date) {
    // Deterministic pseudo-availability based on train+class+date hash
    const seed = (trainNumber + cls + date.toISOString().slice(0, 10))
        .split("")
        .reduce((acc, c) => acc + c.charCodeAt(0), 0);
    const statuses = ["AVAILABLE", "AVAILABLE", "AVAILABLE", "RAC", "WL"];
    const status = statuses[seed % statuses.length];
    const count =
        status === "AVAILABLE"
            ? (seed % 80) + 1
            : status === "RAC"
              ? (seed % 10) + 1
              : (seed % 30) + 1;
    return {
        status,
        count,
        label:
            status === "AVAILABLE"
                ? `AVBL-${count}`
                : status === "RAC"
                  ? `RAC ${count}`
                  : `WL# ${count}`,
    };
}

// ── public functions ──────────────────────────────────────────────────────────

export async function fetchTrainsFromIrctc(
    fromStation: string,
    toStation: string,
    journeyDate: string,
    quota = "GN",
): Promise<object> {
    const from = fromStation.toUpperCase();
    const to = toStation.toUpperCase();

    // Find all trains that have both stations as stops, in order
    const fromStops = await prisma.trainScheduleStop.findMany({
        where: { stationCode: from },
    });
    const toStops = await prisma.trainScheduleStop.findMany({
        where: { stationCode: to },
    });

    const toMap = new Map(toStops.map((s) => [s.trainNumber, s]));

    const trains = fromStops
        .filter((f) => {
            const t = toMap.get(f.trainNumber);
            return t && t.stopNumber > f.stopNumber;
        })
        .map((f) => {
            const t = toMap.get(f.trainNumber)!;
            const depMins =
                parseTime(f.departureTime ?? "00:00") + f.dayOffset * 1440;
            const arrMins =
                parseTime(t.arrivalTime ?? "00:00") + t.dayOffset * 1440;
            const durationMins = arrMins - depMins;
            return {
                trainNumber: f.trainNumber,
                departure: f.departureTime,
                arrival: t.arrivalTime,
                durationMins,
                duration: minutesToHHMM(durationMins),
                fromStation: from,
                toStation: to,
                distance: t.distanceFromOrigin - f.distanceFromOrigin,
            };
        });

    if (trains.length === 0)
        throw new IrctcError(`No trains found between ${from} and ${to}`);

    // Enrich with train master data
    const numbers = trains.map((t) => t.trainNumber);
    const masters = await prisma.train.findMany({
        where: { number: { in: numbers } },
    });
    const masterMap = new Map(masters.map((m) => [m.number, m]));

    return trains.map((t) => ({
        ...t,
        trainName: masterMap.get(t.trainNumber)?.name ?? t.trainNumber,
        type: masterMap.get(t.trainNumber)?.type ?? "EXP",
        classes: masterMap.get(t.trainNumber)?.classes.split(",") ?? [],
        runsDays: masterMap.get(t.trainNumber)?.runsDays ?? "SMTWTFS",
    }));
}

export async function fetchAvailabilityFromIrctc(
    trainNumber: string,
    travelClass: string,
    quota: string,
    journeyDate: string,
): Promise<object> {
    const train = await prisma.train.findUnique({
        where: { number: trainNumber },
    });
    if (!train) throw new IrctcError(`Train ${trainNumber} not found`);

    const classes = train.classes.split(",");
    if (!classes.includes(travelClass)) {
        return {
            available: false,
            reason: `Class ${travelClass} not available on train ${trainNumber}`,
        };
    }

    const date = new Date(journeyDate);
    const avail = availabilityStatus(trainNumber, travelClass, date);
    return {
        trainNumber,
        travelClass,
        quota,
        journeyDate,
        ...avail,
        available: avail.status === "AVAILABLE",
    };
}

export async function fetchFareFromIrctc(
    trainNumber: string,
    travelClass: string,
    quota: string,
    fromStation: string,
    toStation: string,
): Promise<object> {
    const from = fromStation.toUpperCase();
    const to = toStation.toUpperCase();

    const [fromStop, toStop] = await Promise.all([
        prisma.trainScheduleStop.findFirst({
            where: { trainNumber, stationCode: from },
        }),
        prisma.trainScheduleStop.findFirst({
            where: { trainNumber, stationCode: to },
        }),
    ]);

    if (!fromStop || !toStop)
        throw new IrctcError(`Station not found on train ${trainNumber}`);

    const distance = Math.abs(
        toStop.distanceFromOrigin - fromStop.distanceFromOrigin,
    );
    // Base fare: ~0.5 INR per km for SL
    const baseFare = Math.round(distance * 0.5 + 30);
    const amount = fareForClass(baseFare, travelClass, quota);

    return {
        trainNumber,
        travelClass,
        quota,
        fromStation: from,
        toStation: to,
        distance,
        amount,
        currency: "INR",
        breakdown: {
            baseFare,
            reservationCharge: 20,
            superfastCharge: 30,
            gst: Math.round(amount * 0.05),
            total: amount + 20 + 30 + Math.round(amount * 0.05),
        },
    };
}

export async function fetchStationCodeFromIrctc(
    query: string,
): Promise<{ code: string; fullName: string }> {
    const q = query.toUpperCase();
    const station = await prisma.station.findFirst({
        where: {
            OR: [
                { code: { equals: q } },
                { name: { contains: query, mode: "insensitive" } },
                { city: { contains: query, mode: "insensitive" } },
            ],
        },
    });
    if (!station) throw new IrctcError(`Station not found for query: ${query}`);
    return { code: station.code, fullName: station.name };
}

export async function fetchTrainRouteFromIrctc(
    trainNumber: string,
): Promise<object> {
    const stops = await prisma.trainScheduleStop.findMany({
        where: { trainNumber },
        orderBy: { stopNumber: "asc" },
        include: { station: true },
    });
    if (stops.length === 0)
        throw new IrctcError(`Train ${trainNumber} not found`);

    return {
        trainNumber,
        stops: stops.map((s) => ({
            stopNumber: s.stopNumber,
            stationCode: s.stationCode,
            stationName: s.station.name,
            city: s.station.city,
            arrival: s.arrivalTime,
            departure: s.departureTime,
            day: s.dayOffset + 1,
            distance: s.distanceFromOrigin,
        })),
    };
}

export async function fetchSeatMapFromIrctc(
    trainNumber: string,
    travelClass: string,
    journeyDate: string,
): Promise<object> {
    const train = await prisma.train.findUnique({
        where: { number: trainNumber },
    });
    if (!train) throw new IrctcError(`Train ${trainNumber} not found`);

    const date = new Date(journeyDate);
    const seed = (trainNumber + travelClass + date.toISOString().slice(0, 10))
        .split("")
        .reduce((acc, c) => acc + c.charCodeAt(0), 0);

    const coachCount =
        { SL: 8, "3A": 5, "2A": 3, "1A": 2, CC: 6, EC: 2, "2S": 4, VS: 1 }[
            travelClass
        ] ?? 4;
    const seatsPerCoach =
        {
            SL: 72,
            "3A": 64,
            "2A": 46,
            "1A": 24,
            CC: 78,
            EC: 56,
            "2S": 100,
            VS: 44,
        }[travelClass] ?? 60;

    const coaches = Array.from({ length: coachCount }, (_, i) => {
        const coachLabel = `${travelClass}${i + 1}`;
        const bookedCount = (seed * (i + 1)) % Math.floor(seatsPerCoach * 0.8);
        return {
            coach: coachLabel,
            totalSeats: seatsPerCoach,
            bookedSeats: bookedCount,
            availableSeats: seatsPerCoach - bookedCount,
        };
    });

    return { trainNumber, travelClass, journeyDate, coaches };
}

export async function fetchBoardingPointsFromIrctc(
    trainNumber: string,
    fromStation: string,
    journeyDate: string,
): Promise<object> {
    const from = fromStation.toUpperCase();
    const fromStop = await prisma.trainScheduleStop.findFirst({
        where: { trainNumber, stationCode: from },
    });
    if (!fromStop)
        throw new IrctcError(
            `Station ${from} not found on train ${trainNumber}`,
        );

    // Return all usable boarding points on the train.
    const stops = await prisma.trainScheduleStop.findMany({
        where: {
            trainNumber,
            departureTime: { not: null },
        },
        orderBy: { stopNumber: "asc" },
        include: { station: true },
    });

    return {
        trainNumber,
        defaultBoardingPoint: from,
        boardingPoints: stops.map((s) => ({
            stationCode: s.stationCode,
            stationName: s.station.name,
            departure: s.departureTime,
            day: s.dayOffset + 1,
            distance: s.distanceFromOrigin,
        })),
    };
}

export async function fetchTrainByNumberFromIrctc(
    trainNumber: string,
): Promise<object> {
    const train = await prisma.train.findUnique({
        where: { number: trainNumber },
    });
    if (!train) throw new IrctcError(`Train ${trainNumber} not found`);

    const stops = await prisma.trainScheduleStop.findMany({
        where: { trainNumber },
        orderBy: { stopNumber: "asc" },
    });

    const origin = stops[0];
    const dest = stops[stops.length - 1];

    return {
        trainNumber: train.number,
        trainName: train.name,
        type: train.type,
        runsDays: train.runsDays,
        classes: train.classes.split(","),
        origin: origin?.stationCode,
        destination: dest?.stationCode,
        departure: origin?.departureTime,
        arrival: dest?.arrivalTime,
        totalStops: stops.length,
    };
}

export async function fetchLiveStatusFromIrctc(
    trainNumber: string,
    date: string,
): Promise<object> {
    const stops = await prisma.trainScheduleStop.findMany({
        where: { trainNumber },
        orderBy: { stopNumber: "asc" },
        include: { station: true },
    });
    if (stops.length === 0)
        throw new IrctcError(`Train ${trainNumber} not found`);

    // Simulate current position: pick a stop based on current time
    const now = new Date();
    const currentMins = now.getHours() * 60 + now.getMinutes();

    let lastCrossed = stops[0];
    let nextStop = stops[1] ?? stops[0];

    for (let i = 0; i < stops.length - 1; i++) {
        const dep = parseTime(stops[i].departureTime ?? "00:00");
        if (currentMins >= dep) {
            lastCrossed = stops[i];
            nextStop = stops[i + 1];
        }
    }

    const seed = (trainNumber + date)
        .split("")
        .reduce((a, c) => a + c.charCodeAt(0), 0);
    const delayMins = seed % 3 === 0 ? 0 : seed % 15;

    return {
        trainNumber,
        date,
        currentStatus:
            delayMins === 0 ? "ON TIME" : `DELAYED BY ${delayMins} MINS`,
        delayMins,
        lastCrossedStation: {
            code: lastCrossed.stationCode,
            name: lastCrossed.station.name,
            at: lastCrossed.departureTime,
        },
        nextStation: {
            code: nextStop.stationCode,
            name: nextStop.station.name,
            expectedArrival: minutesToHHMM(
                parseTime(nextStop.arrivalTime ?? "00:00") + delayMins,
            ),
        },
    };
}

export async function fetchTrainScheduleFromIrctc(
    trainNumber: string,
): Promise<object> {
    const train = await prisma.train.findUnique({
        where: { number: trainNumber },
    });
    if (!train) throw new IrctcError(`Train ${trainNumber} not found`);

    const stops = await prisma.trainScheduleStop.findMany({
        where: { trainNumber },
        orderBy: { stopNumber: "asc" },
        include: { station: true },
    });

    return {
        trainNumber: train.number,
        trainName: train.name,
        runsDays: train.runsDays,
        schedule: stops.map((s) => ({
            stopNumber: s.stopNumber,
            stationCode: s.stationCode,
            stationName: s.station.name,
            arrival: s.arrivalTime ?? "--",
            departure: s.departureTime ?? "--",
            day: s.dayOffset + 1,
            haltMins:
                s.arrivalTime && s.departureTime
                    ? parseTime(s.departureTime) - parseTime(s.arrivalTime)
                    : 0,
            distance: s.distanceFromOrigin,
        })),
    };
}

export async function fetchPlatformFromIrctc(
    trainNumber: string,
    stationCode: string,
): Promise<object> {
    const code = stationCode.toUpperCase();
    const stop = await prisma.trainScheduleStop.findFirst({
        where: { trainNumber, stationCode: code },
        include: { station: true },
    });
    if (!stop)
        throw new IrctcError(`Train ${trainNumber} does not stop at ${code}`);

    // Deterministic platform number
    const seed = (trainNumber + code)
        .split("")
        .reduce((a, c) => a + c.charCodeAt(0), 0);
    const platform = (seed % 8) + 1;

    return {
        trainNumber,
        stationCode: code,
        stationName: stop.station.name,
        platform,
        scheduledArrival: stop.arrivalTime ?? "--",
        scheduledDeparture: stop.departureTime ?? "--",
    };
}

export async function fetchStationsFromIrctc(query: string): Promise<object> {
    const stations = await prisma.station.findMany({
        where: {
            OR: [
                { code: { contains: query.toUpperCase() } },
                { name: { contains: query, mode: "insensitive" } },
                { city: { contains: query, mode: "insensitive" } },
            ],
        },
        take: 10,
    });
    return {
        stations: stations.map((s) => ({
            code: s.code,
            name: s.name,
            city: s.city,
            state: s.state,
        })),
    };
}

export async function fetchNearbyStationsFromIrctc(
    lat: number,
    lng: number,
): Promise<object> {
    const stations = await prisma.station.findMany({
        where: { lat: { not: null }, lng: { not: null } },
    });

    const withDist = stations
        .map((s) => {
            const dlat = (s.lat! - lat) * 111;
            const dlng = (s.lng! - lng) * 111 * Math.cos((lat * Math.PI) / 180);
            const distKm = Math.sqrt(dlat * dlat + dlng * dlng);
            return {
                code: s.code,
                name: s.name,
                city: s.city,
                state: s.state,
                distKm: Math.round(distKm * 10) / 10,
            };
        })
        .filter((s) => s.distKm <= 50)
        .sort((a, b) => a.distKm - b.distKm)
        .slice(0, 10);

    return { lat, lng, stations: withDist };
}
