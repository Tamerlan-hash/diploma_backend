# Frontend Implementation Instructions for Time Slot Reservations

## Overview

We've added a new API endpoint that allows you to display parking spot reservations grouped by time slots. This feature will help users see which parking spots are reserved at different times.

## API Endpoint

### Time Slot Reservations

**URL**: `/parking/time-slot-reservations/`

**Method**: `GET`

**Authentication**: JWT Token required in the Authorization header

**Query Parameters**:
- `start_time` (required): Start time in ISO format (e.g., "2023-05-01T08:00:00Z")
- `end_time` (required): End time in ISO format (e.g., "2023-05-01T18:00:00Z")
- `interval` (optional, default: 60): Interval in minutes between time slots

**Example Request**:
```javascript
const fetchTimeSlotReservations = async () => {
  const token = localStorage.getItem('token');
  const startTime = '2023-05-01T08:00:00Z';
  const endTime = '2023-05-01T18:00:00Z';
  const interval = 60; // 1 hour intervals
  
  const response = await fetch(
    `/parking/time-slot-reservations/?start_time=${startTime}&end_time=${endTime}&interval=${interval}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  if (response.ok) {
    const data = await response.json();
    return data;
  } else {
    throw new Error('Failed to fetch time slot reservations');
  }
};
```

**Response Format**:
```json
[
  {
    "time_slot": "2023-05-01T08:00:00Z",
    "reservations": [
      {
        "parking_spot_id": "550e8400-e29b-41d4-a716-446655440000",
        "parking_spot_name": "Parking Spot A",
        "is_reserved": true,
        "reservation": {
          "id": 1,
          "user": "john_doe",
          "start_time": "2023-05-01T07:00:00Z",
          "end_time": "2023-05-01T09:00:00Z",
          "status": "active"
        }
      },
      {
        "parking_spot_id": "550e8400-e29b-41d4-a716-446655440001",
        "parking_spot_name": "Parking Spot B",
        "is_reserved": false,
        "reservation": null
      }
      // ... more parking spots
    ]
  },
  {
    "time_slot": "2023-05-01T09:00:00Z",
    "reservations": [
      // ... parking spots with their reservation status at this time slot
    ]
  }
  // ... more time slots
]
```

## Implementation Suggestions

1. **Create a Time Slot Selector Component**:
   - Allow users to select a date range and time interval
   - Use this to fetch data from the API

2. **Create a Time Slot Grid View**:
   - Display time slots as columns
   - Display parking spots as rows
   - Show reservation status using colors (e.g., green for available, red for reserved)
   - Show reservation details on hover or click

3. **Add Filtering Options**:
   - Filter by parking spot name
   - Filter by availability
   - Filter by time range

4. **Add Reservation Creation**:
   - Allow users to click on an available time slot to create a new reservation
   - Use the existing reservation creation endpoint

## Example UI Layout

```
+----------------+----------------+----------------+----------------+
|                | 08:00 - 09:00  | 09:00 - 10:00  | 10:00 - 11:00  |
+----------------+----------------+----------------+----------------+
| Parking Spot A | Reserved       | Available      | Available      |
|                | (John Doe)     |                |                |
+----------------+----------------+----------------+----------------+
| Parking Spot B | Available      | Reserved       | Reserved       |
|                |                | (Jane Smith)   | (Jane Smith)   |
+----------------+----------------+----------------+----------------+
| Parking Spot C | Available      | Available      | Available      |
|                |                |                |                |
+----------------+----------------+----------------+----------------+
```

## Additional Notes

- The API returns all parking spots for each time slot, regardless of whether they are reserved or not.
- The `is_reserved` field indicates whether a parking spot is reserved at that specific time slot.
- If a parking spot is reserved, the `reservation` field contains details about the reservation.
- If a parking spot is not reserved, the `reservation` field is `null`.
- The time slots are generated based on the `start_time`, `end_time`, and `interval` parameters.
- The default interval is 60 minutes (1 hour).

Please let me know if you have any questions or need further clarification.