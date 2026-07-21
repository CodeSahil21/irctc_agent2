from typing import Any, Dict, List, Optional
from langsmith import traceable


@traceable(name="search_trains", run_type="tool")
def search_trains(fromStation: str, toStation: str, journeyDate: str, quota: str = "GN") -> Dict[str, Any]:
    return {
        "trains": [{
            "trainNumber": "12951",
            "trainName": "Mumbai Rajdhani Express",
            "type": "Superfast",
            "departure": "16:55",
            "arrival": "08:35",
            "durationMins": 940,
            "duration": "15h 40m",
            "distance": "1384 km",
            "classes": ["1A", "2A", "3A"],
            "runsDays": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        }]
    }


@traceable(name="check_availability", run_type="tool")
def check_availability(trainNumber: str, travelClass: str, quota: str, journeyDate: str) -> Dict[str, Any]:
    return {
        "trainNumber": trainNumber,
        "travelClass": travelClass,
        "quota": quota,
        "journeyDate": journeyDate,
        "status": "AVAILABLE",
        "count": 42,
        "label": "AVAILABLE-0042",
        "available": True
    }


@traceable(name="get_fare", run_type="tool")
def get_fare(trainNumber: str, travelClass: str, quota: str, fromStation: str, toStation: str) -> Dict[str, Any]:
    return {
        "trainNumber": trainNumber,
        "travelClass": travelClass,
        "quota": quota,
        "fromStation": fromStation,
        "toStation": toStation,
        "distance": "1384 km",
        "amount": 1850.00,
        "currency": "INR",
        "breakdown": {
            "baseFare": 1500.00,
            "reservationCharge": 60.00,
            "superfastCharge": 75.00,
            "gst": 215.00,
            "total": 1850.00
        }
    }


@traceable(name="get_route", run_type="tool")
def get_route(trainNumber: str) -> Dict[str, Any]:
    return {
        "trainNumber": trainNumber,
        "stops": [
            {"stopNumber": 1, "stationCode": "NDLS", "stationName": "New Delhi", "city": "Delhi", "arrival": "16:55", "departure": "16:55", "day": 1, "distance": 0},
            {"stopNumber": 2, "stationCode": "KOTA", "stationName": "Kota Junction", "city": "Kota", "arrival": "21:35", "departure": "21:45", "day": 1, "distance": 465},
            {"stopNumber": 3, "stationCode": "BCT", "stationName": "Mumbai Central", "city": "Mumbai", "arrival": "08:35", "departure": "08:35", "day": 2, "distance": 1384}
        ]
    }


@traceable(name="get_seat_map", run_type="tool")
def get_seat_map(trainNumber: str, travelClass: str, journeyDate: str) -> Dict[str, Any]:
    return {
        "trainNumber": trainNumber,
        "travelClass": travelClass,
        "journeyDate": journeyDate,
        "coaches": [
            {"coach": "B1", "totalSeats": 64, "bookedSeats": 50, "availableSeats": 14},
            {"coach": "B2", "totalSeats": 64, "bookedSeats": 48, "availableSeats": 16}
        ]
    }


@traceable(name="get_boarding_points", run_type="tool")
def get_boarding_points(trainNumber: str, fromStation: str, journeyDate: str) -> Dict[str, Any]:
    return {
        "trainNumber": trainNumber,
        "defaultBoardingPoint": fromStation,
        "boardingPoints": [
            {"stationCode": "NDLS", "stationName": "New Delhi", "departure": "16:55", "day": 1, "distance": 0},
            {"stationCode": "NZM", "stationName": "Hazrat Nizamuddin", "departure": "17:15", "day": 1, "distance": 7}
        ]
    }


@traceable(name="search_train_by_number", run_type="tool")
def search_train_by_number(trainNumber: str) -> Dict[str, Any]:
    return {
        "trainNumber": trainNumber,
        "trainName": "August Kranti Rajdhani",
        "type": "Rajdhani",
        "runsDays": ["DAILY"],
        "classes": ["1A", "2A", "3A"],
        "origin": "NZM",
        "destination": "BCT",
        "departure": "17:15",
        "arrival": "10:05",
        "totalStops": 12
    }


@traceable(name="get_live_status", run_type="tool")
def get_live_status(trainNumber: str, date: str) -> Dict[str, Any]:
    return {
        "trainNumber": trainNumber,
        "date": date,
        "currentStatus": "RUNNING",
        "delayMins": 15,
        "lastCrossedStation": {"code": "KOTA", "name": "Kota Junction", "at": "21:50"},
        "nextStation": {"code": "RTM", "name": "Ratlam Junction", "expectedArrival": "00:20"}
    }


@traceable(name="get_train_schedule", run_type="tool")
def get_train_schedule(trainNumber: str) -> Dict[str, Any]:
    return {
        "trainNumber": trainNumber,
        "trainName": "Tamil Nadu Express",
        "runsDays": ["DAILY"],
        "schedule": [
            {"stopNumber": 1, "stationCode": "NDLS", "stationName": "New Delhi", "arrival": "22:30", "departure": "22:30", "day": 1, "haltMins": 0, "distance": 0},
            {"stopNumber": 2, "stationCode": "MAS", "stationName": "Chennai Central", "arrival": "06:10", "departure": "06:10", "day": 3, "haltMins": 0, "distance": 2182}
        ]
    }


@traceable(name="get_platform", run_type="tool")
def get_platform(trainNumber: str, stationCode: str) -> Dict[str, Any]:
    return {
        "trainNumber": trainNumber,
        "stationCode": stationCode,
        "stationName": "New Delhi",
        "platform": "16",
        "scheduledArrival": "16:30",
        "scheduledDeparture": "16:55"
    }


@traceable(name="search_stations", run_type="tool")
def search_stations(query: str) -> Dict[str, Any]:
    return {
        "stations": [
            {"code": "BCT", "name": "Mumbai Central", "city": "Mumbai", "state": "Maharashtra"},
            {"code": "CSMT", "name": "Chhatrapati Shivaji Maharaj Terminus", "city": "Mumbai", "state": "Maharashtra"}
        ]
    }


@traceable(name="find_station_code", run_type="tool")
def find_station_code(query: str) -> Dict[str, Any]:
    return {"code": "NDLS", "fullName": "New Delhi"}


@traceable(name="get_nearby_stations", run_type="tool")
def get_nearby_stations(lat: float, lng: float) -> Dict[str, Any]:
    return {
        "lat": lat, "lng": lng,
        "stations": [
            {"code": "NDLS", "name": "New Delhi", "city": "Delhi", "state": "Delhi", "distKm": 2.3},
            {"code": "NZM", "name": "Hazrat Nizamuddin", "city": "Delhi", "state": "Delhi", "distKm": 6.8}
        ]
    }


@traceable(name="list_classes", run_type="tool")
def list_classes() -> List[Dict[str, str]]:
    return [
        {"code": "SL", "name": "Sleeper"},
        {"code": "3A", "name": "AC 3 Tier"},
        {"code": "2A", "name": "AC 2 Tier"},
        {"code": "1A", "name": "AC First Class"},
        {"code": "CC", "name": "AC Chair Car"},
        {"code": "EC", "name": "Executive Chair Car"},
        {"code": "2S", "name": "Second Sitting"},
        {"code": "VS", "name": "Vistadome AC"}
    ]


@traceable(name="list_quotas", run_type="tool")
def list_quotas() -> List[Dict[str, str]]:
    return [
        {"code": "GN", "name": "General"},
        {"code": "LD", "name": "Ladies"},
        {"code": "TQ", "name": "Tatkal"},
        {"code": "PT", "name": "Premium Tatkal"},
        {"code": "HO", "name": "Higher Official"},
        {"code": "SS", "name": "Senior Citizen"}
    ]


@traceable(name="recommend_trains", run_type="tool")
def recommend_trains(fromStation: str, toStation: str, journeyDate: str, preference: str, travelClass: str = "SL", quota: str = "GN") -> Dict[str, Any]:
    return {
        "trains": [{
            "trainNumber": "12951",
            "trainName": "Mumbai Rajdhani Express",
            "preferenceRank": 1,
            "availability": "AVAILABLE-0042",
            "fare": 1850.00
        }]
    }


@traceable(name="book_ticket", run_type="tool")
def book_ticket(trainNumber: str, trainName: str, source: str, destination: str, journeyDate: str, travelClass: str, quota: str, fare: float, passengers: list) -> Dict[str, Any]:
    return {
        "id": "bk-998877",
        "pnr": "4521367890",
        "status": "PENDING",
        "trainNumber": trainNumber,
        "trainName": trainName,
        "source": source,
        "destination": destination,
        "journeyDate": journeyDate,
        "travelClass": travelClass,
        "quota": quota,
        "fare": fare,
        "passengerCount": len(passengers),
        "passengers": passengers
    }


@traceable(name="cancel_ticket", run_type="tool")
def cancel_ticket(pnr: str) -> Dict[str, Any]:
    return {"pnr": pnr, "updatedCount": 1, "status": "CANCELLED"}


@traceable(name="get_pnr", run_type="tool")
def get_pnr(pnr: str) -> Dict[str, Any]:
    return {
        "id": "pnr-tr-123",
        "userId": "usr_test@example.com",
        "pnr": pnr,
        "lastStatus": "CONFIRMED / B3-34",
        "checkedAt": "2026-07-21T15:00:00Z"
    }


@traceable(name="get_booking", run_type="tool")
def get_booking(pnr: str) -> Dict[str, Any]:
    return {
        "id": "bk-998877",
        "pnr": pnr,
        "status": "BOOKED",
        "trainNumber": "12951",
        "trainName": "Mumbai Rajdhani Express",
        "source": "NDLS",
        "destination": "BCT",
        "journeyDate": "2026-08-15",
        "passengers": [{"name": "Rahul Sharma", "age": 28, "gender": "MALE", "berth": "LB"}]
    }


@traceable(name="get_booking_history", run_type="tool")
def get_booking_history() -> List[Dict[str, Any]]:
    return [{
        "id": "bk-998877",
        "pnr": "4521367890",
        "status": "BOOKED",
        "trainNumber": "12951",
        "journeyDate": "2026-08-15",
        "passengers": [{"name": "Rahul Sharma", "age": 28, "gender": "MALE"}]
    }]


@traceable(name="update_booking_status", run_type="tool")
def update_booking_status(pnr: str, status: str, transactionId: Optional[str] = None) -> Dict[str, Any]:
    return {"pnr": pnr, "status": status, "transactionId": transactionId, "updatedCount": 1}


@traceable(name="update_boarding_point", run_type="tool")
def update_boarding_point(pnr: str, newBoardingStation: str) -> Dict[str, Any]:
    return {"pnr": pnr, "newBoardingStation": newBoardingStation, "status": "UPDATED"}


@traceable(name="create_reminder", run_type="tool")
def create_reminder(reminder_type: str, reminderAt: str, bookingId: Optional[str] = None, metadata: Optional[dict] = None) -> Dict[str, Any]:
    return {
        "id": "rem-001122",
        "userId": "usr_test@example.com",
        "type": reminder_type,
        "reminderAt": reminderAt,
        "bookingId": bookingId,
        "metadata": metadata or {},
        "sent": False,
        "createdAt": "2026-07-21T15:10:00Z"
    }


@traceable(name="get_reminders", run_type="tool")
def get_reminders() -> List[Dict[str, Any]]:
    return [{
        "id": "rem-001122",
        "type": "JOURNEY",
        "reminderAt": "2026-08-14T18:00:00.000Z",
        "sent": False
    }]


@traceable(name="update_reminder", run_type="tool")
def update_reminder(reminderId: str, reminderAt: Optional[str] = None, reminder_type: Optional[str] = None, metadata: Optional[dict] = None) -> Dict[str, Any]:
    return {"reminderId": reminderId, "reminderAt": reminderAt, "status": "UPDATED"}


@traceable(name="delete_reminder", run_type="tool")
def delete_reminder(reminderId: str) -> Dict[str, Any]:
    return {"reminderId": reminderId, "deleted": True}


@traceable(name="add_saved_passenger", run_type="tool")
def add_saved_passenger(name: str, age: int, gender: str, berthPreference: Optional[str] = None, seniorCitizen: bool = False) -> Dict[str, Any]:
    return {
        "id": "pass-7788",
        "userId": "usr_test@example.com",
        "name": name,
        "age": age,
        "gender": gender,
        "berthPreference": berthPreference,
        "seniorCitizen": seniorCitizen,
        "createdAt": "2026-07-21T15:12:00Z"
    }


@traceable(name="get_saved_passengers", run_type="tool")
def get_saved_passengers() -> List[Dict[str, Any]]:
    return [{
        "id": "pass-7788",
        "name": "Rahul Sharma",
        "age": 28,
        "gender": "MALE",
        "berthPreference": "LB",
        "seniorCitizen": False
    }]
