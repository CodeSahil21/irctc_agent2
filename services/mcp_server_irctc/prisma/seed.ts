import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient({});

const stations = [
    {
        code: "NDLS",
        name: "New Delhi",
        city: "New Delhi",
        state: "Delhi",
        zone: "NR",
        lat: 28.6419,
        lng: 77.2194,
    },
    {
        code: "BCT",
        name: "Mumbai Central",
        city: "Mumbai",
        state: "Maharashtra",
        zone: "WR",
        lat: 18.9696,
        lng: 72.8194,
    },
    {
        code: "HWH",
        name: "Howrah Junction",
        city: "Kolkata",
        state: "West Bengal",
        zone: "ER",
        lat: 22.5839,
        lng: 88.3424,
    },
    {
        code: "MAS",
        name: "Chennai Central",
        city: "Chennai",
        state: "Tamil Nadu",
        zone: "SR",
        lat: 13.0827,
        lng: 80.2707,
    },
    {
        code: "SBC",
        name: "Bengaluru City Junction",
        city: "Bengaluru",
        state: "Karnataka",
        zone: "SWR",
        lat: 12.9784,
        lng: 77.5718,
    },
    {
        code: "HYB",
        name: "Hyderabad Deccan",
        city: "Hyderabad",
        state: "Telangana",
        zone: "SCR",
        lat: 17.385,
        lng: 78.4867,
    },
    {
        code: "PUNE",
        name: "Pune Junction",
        city: "Pune",
        state: "Maharashtra",
        zone: "CR",
        lat: 18.5204,
        lng: 73.8567,
    },
    {
        code: "ADI",
        name: "Ahmedabad Junction",
        city: "Ahmedabad",
        state: "Gujarat",
        zone: "WR",
        lat: 23.0225,
        lng: 72.5714,
    },
    {
        code: "JP",
        name: "Jaipur Junction",
        city: "Jaipur",
        state: "Rajasthan",
        zone: "NWR",
        lat: 26.9124,
        lng: 75.7873,
    },
    {
        code: "LKO",
        name: "Lucknow Charbagh",
        city: "Lucknow",
        state: "Uttar Pradesh",
        zone: "NR",
        lat: 26.8467,
        lng: 80.9462,
    },
    {
        code: "PNBE",
        name: "Patna Junction",
        city: "Patna",
        state: "Bihar",
        zone: "ECR",
        lat: 25.5941,
        lng: 85.1376,
    },
    {
        code: "BPL",
        name: "Bhopal Junction",
        city: "Bhopal",
        state: "Madhya Pradesh",
        zone: "WCR",
        lat: 23.2599,
        lng: 77.4126,
    },
    {
        code: "NGP",
        name: "Nagpur Junction",
        city: "Nagpur",
        state: "Maharashtra",
        zone: "CR",
        lat: 21.1458,
        lng: 79.0882,
    },
    {
        code: "SC",
        name: "Secunderabad Junction",
        city: "Hyderabad",
        state: "Telangana",
        zone: "SCR",
        lat: 17.4344,
        lng: 78.5013,
    },
    {
        code: "CSTM",
        name: "Chhatrapati Shivaji Maharaj Terminus",
        city: "Mumbai",
        state: "Maharashtra",
        zone: "CR",
        lat: 18.9398,
        lng: 72.8355,
    },
    {
        code: "AGC",
        name: "Agra Cantt",
        city: "Agra",
        state: "Uttar Pradesh",
        zone: "NCR",
        lat: 27.1767,
        lng: 78.0081,
    },
    {
        code: "MTJ",
        name: "Mathura Junction",
        city: "Mathura",
        state: "Uttar Pradesh",
        zone: "NCR",
        lat: 27.4924,
        lng: 77.6737,
    },
    {
        code: "GWL",
        name: "Gwalior Junction",
        city: "Gwalior",
        state: "Madhya Pradesh",
        zone: "NCR",
        lat: 26.2183,
        lng: 78.1828,
    },
    {
        code: "JHS",
        name: "Jhansi Junction",
        city: "Jhansi",
        state: "Uttar Pradesh",
        zone: "NCR",
        lat: 25.4484,
        lng: 78.5685,
    },
    {
        code: "VSKP",
        name: "Visakhapatnam Junction",
        city: "Visakhapatnam",
        state: "Andhra Pradesh",
        zone: "ECoR",
        lat: 17.6868,
        lng: 83.2185,
    },
    {
        code: "BZA",
        name: "Vijayawada Junction",
        city: "Vijayawada",
        state: "Andhra Pradesh",
        zone: "SCR",
        lat: 16.5062,
        lng: 80.648,
    },
    {
        code: "GNT",
        name: "Guntur Junction",
        city: "Guntur",
        state: "Andhra Pradesh",
        zone: "SCR",
        lat: 16.3067,
        lng: 80.4365,
    },
    {
        code: "RJY",
        name: "Rajahmundry",
        city: "Rajahmundry",
        state: "Andhra Pradesh",
        zone: "SCR",
        lat: 17.0005,
        lng: 81.804,
    },
    {
        code: "TPTY",
        name: "Tirupati",
        city: "Tirupati",
        state: "Andhra Pradesh",
        zone: "SCR",
        lat: 13.6288,
        lng: 79.4192,
    },
    {
        code: "CBE",
        name: "Coimbatore Junction",
        city: "Coimbatore",
        state: "Tamil Nadu",
        zone: "SR",
        lat: 11.0168,
        lng: 76.9558,
    },
    {
        code: "MDU",
        name: "Madurai Junction",
        city: "Madurai",
        state: "Tamil Nadu",
        zone: "SR",
        lat: 9.9252,
        lng: 78.1198,
    },
    {
        code: "TVC",
        name: "Thiruvananthapuram Central",
        city: "Thiruvananthapuram",
        state: "Kerala",
        zone: "SR",
        lat: 8.4855,
        lng: 76.9492,
    },
    {
        code: "ERS",
        name: "Ernakulam Junction",
        city: "Kochi",
        state: "Kerala",
        zone: "SR",
        lat: 9.9816,
        lng: 76.2999,
    },
    {
        code: "SUR",
        name: "Solapur Junction",
        city: "Solapur",
        state: "Maharashtra",
        zone: "CR",
        lat: 17.6868,
        lng: 75.9064,
    },
    {
        code: "DD",
        name: "Dadar",
        city: "Mumbai",
        state: "Maharashtra",
        zone: "CR",
        lat: 19.0178,
        lng: 72.8478,
    },
    {
        code: "MGS",
        name: "Mughal Sarai Junction",
        city: "Chandauli",
        state: "Uttar Pradesh",
        zone: "ECR",
        lat: 25.28,
        lng: 83.119,
    },
    {
        code: "BRC",
        name: "Vadodara Junction",
        city: "Vadodara",
        state: "Gujarat",
        zone: "WR",
        lat: 22.3119,
        lng: 73.1723,
    },
    {
        code: "RTM",
        name: "Ratlam Junction",
        city: "Ratlam",
        state: "Madhya Pradesh",
        zone: "WR",
        lat: 23.3315,
        lng: 75.0367,
    },
    {
        code: "KOTA",
        name: "Kota Junction",
        city: "Kota",
        state: "Rajasthan",
        zone: "WCR",
        lat: 25.1802,
        lng: 75.833,
    },
    {
        code: "RU",
        name: "Arakkonam Junction",
        city: "Arakkonam",
        state: "Tamil Nadu",
        zone: "SR",
        lat: 13.0785,
        lng: 79.671,
    },
];

const trains = [
    {
        number: "12301",
        name: "Howrah Rajdhani Express",
        type: "RAJ",
        runsDays: "SMTWTFS",
        classes: "1A,2A,3A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12302",
        name: "New Delhi Rajdhani Express",
        type: "RAJ",
        runsDays: "SMTWTFS",
        classes: "1A,2A,3A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12951",
        name: "Mumbai Rajdhani Express",
        type: "RAJ",
        runsDays: "SMTWTFS",
        classes: "1A,2A,3A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12952",
        name: "New Delhi Rajdhani Express",
        type: "RAJ",
        runsDays: "SMTWTFS",
        classes: "1A,2A,3A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12621",
        name: "Tamil Nadu Express",
        type: "SF",
        runsDays: "SMTWTFS",
        classes: "SL,3A,2A,1A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12622",
        name: "Tamil Nadu Express",
        type: "SF",
        runsDays: "SMTWTFS",
        classes: "SL,3A,2A,1A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12001",
        name: "Bhopal Shatabdi Express",
        type: "SHT",
        runsDays: "SMTWTF_",
        classes: "CC,EC",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12002",
        name: "New Delhi Shatabdi Express",
        type: "SHT",
        runsDays: "SMTWTF_",
        classes: "CC,EC",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12627",
        name: "Karnataka Express",
        type: "SF",
        runsDays: "SMTWTFS",
        classes: "SL,3A,2A,1A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12628",
        name: "Karnataka Express",
        type: "SF",
        runsDays: "SMTWTFS",
        classes: "SL,3A,2A,1A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12723",
        name: "Telangana Express",
        type: "SF",
        runsDays: "SMTWTFS",
        classes: "SL,3A,2A,1A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12724",
        name: "Telangana Express",
        type: "SF",
        runsDays: "SMTWTFS",
        classes: "SL,3A,2A,1A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12431",
        name: "Thiruvananthapuram Rajdhani",
        type: "RAJ",
        runsDays: "_M_W_F_",
        classes: "1A,2A,3A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12432",
        name: "Hazrat Nizamuddin Rajdhani",
        type: "RAJ",
        runsDays: "_M_W_F_",
        classes: "1A,2A,3A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "22691",
        name: "Rajdhani Express",
        type: "RAJ",
        runsDays: "S_T_T_S",
        classes: "1A,2A,3A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "22692",
        name: "Rajdhani Express",
        type: "RAJ",
        runsDays: "S_T_T_S",
        classes: "1A,2A,3A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12259",
        name: "Sealdah Duronto Express",
        type: "DUR",
        runsDays: "_M___F_",
        classes: "SL,3A,2A,1A",
        quotas: "GN,TQ,PT",
    },
    {
        number: "12260",
        name: "New Delhi Duronto Express",
        type: "DUR",
        runsDays: "__T___S",
        classes: "SL,3A,2A,1A",
        quotas: "GN,TQ,PT",
    },
    {
        number: "12309",
        name: "Rajendra Nagar Patna Rajdhani",
        type: "RAJ",
        runsDays: "SMTWTFS",
        classes: "1A,2A,3A",
        quotas: "GN,TQ,PT,LD,SS",
    },
    {
        number: "12310",
        name: "New Delhi Rajdhani Express",
        type: "RAJ",
        runsDays: "SMTWTFS",
        classes: "1A,2A,3A",
        quotas: "GN,TQ,PT,LD,SS",
    },
];

// Schedule stops: [trainNumber, stationCode, arrival, departure, dayOffset, stopNumber, distance]
type StopRow = [
    string,
    string,
    string | null,
    string | null,
    number,
    number,
    number,
];

const scheduleStops: StopRow[] = [
    // 12301 Howrah Rajdhani (HWH -> NDLS)
    ["12301", "HWH", null, "16:55", 0, 1, 0],
    ["12301", "PNBE", "22:45", "22:55", 0, 2, 531],
    ["12301", "MGS", "01:10", "01:20", 1, 3, 760],
    ["12301", "NDLS", "10:00", null, 1, 4, 1441],

    // 12302 New Delhi Rajdhani (NDLS -> HWH)
    ["12302", "NDLS", null, "17:00", 0, 1, 0],
    ["12302", "MGS", "01:35", "01:40", 1, 2, 681],
    ["12302", "PNBE", "03:55", "04:05", 1, 3, 910],
    ["12302", "HWH", "10:05", null, 1, 4, 1441],

    // 12951 Mumbai Rajdhani (BCT -> NDLS)
    ["12951", "BCT", null, "17:00", 0, 1, 0],
    ["12951", "BRC", "19:40", "19:45", 0, 2, 100],
    ["12951", "RTM", "22:30", "22:35", 0, 3, 280],
    ["12951", "KOTA", "01:45", "01:50", 1, 4, 480],
    ["12951", "MTJ", "05:50", "05:52", 1, 5, 900],
    ["12951", "NDLS", "08:35", null, 1, 6, 1384],

    // 12952 New Delhi Rajdhani (NDLS -> BCT)
    ["12952", "NDLS", null, "16:25", 0, 1, 0],
    ["12952", "MTJ", "18:55", "18:57", 0, 2, 141],
    ["12952", "KOTA", "23:15", "23:20", 0, 3, 561],
    ["12952", "RTM", "01:45", "01:50", 1, 4, 761],
    ["12952", "BRC", "04:25", "04:30", 1, 5, 941],
    ["12952", "BCT", "07:40", null, 1, 6, 1384],

    // 12621 Tamil Nadu Express (MAS -> NDLS)
    ["12621", "MAS", null, "22:00", 0, 1, 0],
    ["12621", "RU", "23:30", "23:35", 0, 2, 90],
    ["12621", "BZA", "04:45", "05:00", 1, 3, 432],
    ["12621", "NGP", "14:05", "14:15", 1, 4, 1074],
    ["12621", "BPL", "22:00", "22:10", 1, 5, 1446],
    ["12621", "AGC", "04:00", "04:05", 2, 6, 1888],
    ["12621", "NDLS", "07:55", null, 2, 7, 2188],

    // 12622 Tamil Nadu Express (NDLS -> MAS)
    ["12622", "NDLS", null, "22:30", 0, 1, 0],
    ["12622", "AGC", "01:38", "01:40", 1, 2, 200],
    ["12622", "BPL", "09:00", "09:10", 1, 3, 742],
    ["12622", "NGP", "17:05", "17:15", 1, 4, 1114],
    ["12622", "BZA", "03:00", "03:15", 2, 5, 1756],
    ["12622", "MAS", "08:30", null, 2, 6, 2188],

    // 12001 Bhopal Shatabdi (NDLS -> BPL)
    ["12001", "NDLS", null, "06:00", 0, 1, 0],
    ["12001", "AGC", "08:10", "08:15", 0, 2, 200],
    ["12001", "GWL", "09:25", "09:30", 0, 3, 319],
    ["12001", "JHS", "10:40", "10:45", 0, 4, 410],
    ["12001", "BPL", "14:00", null, 0, 5, 704],

    // 12002 New Delhi Shatabdi (BPL -> NDLS)
    ["12002", "BPL", null, "15:00", 0, 1, 0],
    ["12002", "JHS", "18:15", "18:20", 0, 2, 294],
    ["12002", "GWL", "19:30", "19:35", 0, 3, 385],
    ["12002", "AGC", "20:45", "20:50", 0, 4, 504],
    ["12002", "NDLS", "22:30", null, 0, 5, 704],

    // 12627 Karnataka Express (NDLS -> SBC)
    ["12627", "NDLS", null, "22:30", 0, 1, 0],
    ["12627", "MTJ", "00:55", "01:00", 1, 2, 141],
    ["12627", "AGC", "02:00", "02:05", 1, 3, 200],
    ["12627", "GWL", "03:55", "04:00", 1, 4, 319],
    ["12627", "JHS", "05:30", "05:35", 1, 5, 410],
    ["12627", "BPL", "09:30", "09:40", 1, 6, 704],
    ["12627", "NGP", "16:30", "16:40", 1, 7, 1176],
    ["12627", "SC", "02:00", "02:10", 2, 8, 1660],
    ["12627", "SBC", "11:00", null, 2, 9, 2056],

    // 12628 Karnataka Express (SBC -> NDLS)
    ["12628", "SBC", null, "20:15", 0, 1, 0],
    ["12628", "SC", "05:00", "05:10", 1, 2, 396],
    ["12628", "NGP", "14:30", "14:40", 1, 3, 880],
    ["12628", "BPL", "21:30", "21:40", 1, 4, 1352],
    ["12628", "JHS", "01:30", "01:35", 2, 5, 1646],
    ["12628", "GWL", "03:00", "03:05", 2, 6, 1737],
    ["12628", "AGC", "04:20", "04:25", 2, 7, 1856],
    ["12628", "MTJ", "05:15", "05:20", 2, 8, 1915],
    ["12628", "NDLS", "07:30", null, 2, 9, 2056],

    // 12723 Telangana Express (HYB -> NDLS)
    ["12723", "HYB", null, "18:05", 0, 1, 0],
    ["12723", "SC", "18:30", "18:40", 0, 2, 10],
    ["12723", "NGP", "02:30", "02:40", 1, 3, 502],
    ["12723", "BPL", "09:30", "09:40", 1, 4, 974],
    ["12723", "JHS", "13:00", "13:05", 1, 5, 1268],
    ["12723", "AGC", "17:30", "17:35", 1, 6, 1612],
    ["12723", "NDLS", "20:30", null, 1, 7, 1794],

    // 12724 Telangana Express (NDLS -> HYB)
    ["12724", "NDLS", null, "06:25", 0, 1, 0],
    ["12724", "AGC", "09:00", "09:05", 0, 2, 182],
    ["12724", "JHS", "13:00", "13:05", 0, 3, 526],
    ["12724", "BPL", "16:30", "16:40", 0, 4, 820],
    ["12724", "NGP", "23:30", "23:40", 0, 5, 1292],
    ["12724", "SC", "11:00", "11:10", 1, 6, 1784],
    ["12724", "HYB", "11:35", null, 1, 7, 1794],

    // 12431 Thiruvananthapuram Rajdhani (NDLS -> TVC)
    ["12431", "NDLS", null, "11:00", 0, 1, 0],
    ["12431", "BPL", "21:30", "21:40", 0, 2, 704],
    ["12431", "NGP", "04:30", "04:40", 1, 3, 1176],
    ["12431", "SC", "14:00", "14:10", 1, 4, 1660],
    ["12431", "CBE", "03:00", "03:10", 2, 5, 2600],
    ["12431", "ERS", "07:30", "07:40", 2, 6, 2800],
    ["12431", "TVC", "11:30", null, 2, 7, 3100],

    // 12432 Hazrat Nizamuddin Rajdhani (TVC -> NDLS)
    ["12432", "TVC", null, "13:30", 0, 1, 0],
    ["12432", "ERS", "17:30", "17:40", 0, 2, 300],
    ["12432", "CBE", "21:30", "21:40", 0, 3, 500],
    ["12432", "SC", "10:30", "10:40", 1, 4, 1440],
    ["12432", "NGP", "20:00", "20:10", 1, 5, 1924],
    ["12432", "BPL", "03:00", "03:10", 2, 6, 2396],
    ["12432", "NDLS", "13:30", null, 2, 7, 3100],

    // 22691 Rajdhani Express (SBC -> NDLS)
    ["22691", "SBC", null, "20:00", 0, 1, 0],
    ["22691", "SC", "04:30", "04:40", 1, 2, 396],
    ["22691", "NGP", "14:00", "14:10", 1, 3, 880],
    ["22691", "BPL", "21:00", "21:10", 1, 4, 1352],
    ["22691", "NDLS", "08:00", null, 2, 5, 2056],

    // 22692 Rajdhani Express (NDLS -> SBC)
    ["22692", "NDLS", null, "20:30", 0, 1, 0],
    ["22692", "BPL", "07:30", "07:40", 1, 2, 704],
    ["22692", "NGP", "14:30", "14:40", 1, 3, 1176],
    ["22692", "SC", "00:00", "00:10", 2, 4, 1660],
    ["22692", "SBC", "08:30", null, 2, 5, 2056],

    // 12259 Sealdah Duronto (NDLS -> HWH)
    ["12259", "NDLS", null, "23:00", 0, 1, 0],
    ["12259", "PNBE", "09:30", "09:40", 1, 2, 910],
    ["12259", "HWH", "15:30", null, 1, 3, 1441],

    // 12260 New Delhi Duronto (HWH -> NDLS)
    ["12260", "HWH", null, "08:15", 0, 1, 0],
    ["12260", "PNBE", "14:00", "14:10", 0, 2, 531],
    ["12260", "NDLS", "00:30", null, 1, 3, 1441],

    // 12309 Patna Rajdhani (NDLS -> PNBE)
    ["12309", "NDLS", null, "18:25", 0, 1, 0],
    ["12309", "LKO", "00:30", "00:40", 1, 2, 512],
    ["12309", "PNBE", "07:45", null, 1, 3, 1001],

    // 12310 New Delhi Rajdhani (PNBE -> NDLS)
    ["12310", "PNBE", null, "19:00", 0, 1, 0],
    ["12310", "LKO", "02:15", "02:25", 1, 2, 489],
    ["12310", "NDLS", "08:30", null, 1, 3, 1001],
];

async function main() {
    console.log("Seeding stations...");
    for (const s of stations) {
        await prisma.station.upsert({
            where: { code: s.code },
            update: s,
            create: s,
        });
    }

    console.log("Seeding trains...");
    for (const t of trains) {
        await prisma.train.upsert({
            where: { number: t.number },
            update: t,
            create: t,
        });
    }

    console.log("Seeding schedule stops...");
    for (const [
        trainNumber,
        stationCode,
        arrivalTime,
        departureTime,
        dayOffset,
        stopNumber,
        distanceFromOrigin,
    ] of scheduleStops) {
        const stop = await prisma.trainScheduleStop.findFirst({
            where: { trainNumber, stationCode },
        });
        const stationName =
            stations.find((s) => s.code === stationCode)?.name ?? stationCode;
        const data = {
            trainNumber,
            stationCode,
            stationName,
            arrivalTime,
            departureTime,
            dayOffset,
            stopNumber,
            distanceFromOrigin,
        };
        if (stop) {
            await prisma.trainScheduleStop.update({
                where: { id: stop.id },
                data,
            });
        } else {
            await prisma.trainScheduleStop.create({ data });
        }
    }

    console.log(
        `Seeded ${stations.length} stations, ${trains.length} trains, ${scheduleStops.length} stops.`,
    );
}

main()
    .catch(console.error)
    .finally(() => prisma.$disconnect());
