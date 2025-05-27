# Frontend Timezone Handling Instructions

## Overview

This document provides instructions for correctly handling timezone information in datetime values received from the backend. Incorrect timezone handling is causing issues with the calculation of reservation slot blocking times on the frontend.

## Problem Description

The backend sends all datetime values in UTC timezone (with 'Z' suffix, e.g., "2023-05-01T08:00:00Z"). However, the frontend may be interpreting these as local times or not applying the correct timezone conversion, leading to incorrect display and calculation of reservation slot times.

## Solution

### 1. Parsing ISO Datetime Strings

When parsing ISO datetime strings received from the API, make sure to preserve the timezone information:

```javascript
// Correct way to parse ISO datetime string
const parseISODateTime = (isoString) => {
  return new Date(isoString);
};

// Example
const utcDateTime = parseISODateTime("2023-05-01T08:00:00Z");
console.log(utcDateTime.toISOString()); // "2023-05-01T08:00:00.000Z"
```

### 2. Converting UTC to Local Time for Display

When displaying times to users, convert UTC times to local timezone:

```javascript
// Convert UTC time to local time for display
const formatLocalDateTime = (utcDateTime) => {
  return new Intl.DateTimeFormat('default', {
    year: 'numeric',
    month: 'numeric',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
    timeZoneName: 'short'
  }).format(utcDateTime);
};

// Example
const utcDateTime = new Date("2023-05-01T08:00:00Z");
console.log(formatLocalDateTime(utcDateTime)); // e.g., "5/1/2023, 10:00 AM GMT+2" (depends on user's timezone)
```

### 3. Sending Times to the Backend

When sending times to the backend, ensure they are in UTC format:

```javascript
// Convert local time to UTC for sending to backend
const getUTCISOString = (localDateTime) => {
  return localDateTime.toISOString();
};

// Example
const localDateTime = new Date(); // Current local time
const utcString = getUTCISOString(localDateTime);
console.log(utcString); // e.g., "2023-05-01T08:00:00.000Z"
```

### 4. Comparing Times

When comparing times (e.g., to determine if a slot is blocked), ensure you're comparing times in the same timezone:

```javascript
// Compare times in UTC
const isTimeInPast = (timeToCheck) => {
  const now = new Date();
  const utcTimeToCheck = new Date(timeToCheck);
  return utcTimeToCheck < now;
};

// Example
const slotEndTime = "2023-05-01T08:00:00Z";
console.log(isTimeInPast(slotEndTime)); // true or false depending on current time
```

### 5. Displaying Time Slots

When displaying time slots in a grid or list, ensure consistent timezone handling:

```javascript
// Format time slot for display
const formatTimeSlot = (timeSlot) => {
  const date = new Date(timeSlot);
  return date.toLocaleTimeString('default', {
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Example
const timeSlots = ["2023-05-01T08:00:00Z", "2023-05-01T09:00:00Z", "2023-05-01T10:00:00Z"];
const formattedSlots = timeSlots.map(formatTimeSlot);
console.log(formattedSlots); // e.g., ["10:00 AM", "11:00 AM", "12:00 PM"] (depends on user's timezone)
```

## Common Pitfalls

1. **Using `new Date()` without timezone consideration**: This creates a date in the local timezone, which may lead to incorrect comparisons with UTC dates from the backend.

2. **Manually parsing date strings**: Avoid manually parsing date strings (e.g., splitting by 'T' or ':'). Use the built-in `Date` constructor or libraries like moment.js or date-fns.

3. **Ignoring the 'Z' suffix**: The 'Z' suffix in ISO datetime strings indicates UTC timezone. Make sure your parsing logic preserves this information.

4. **Inconsistent timezone handling**: Use the same approach for all datetime operations in your application to avoid inconsistencies.

## Recommended Libraries

For more complex datetime operations, consider using one of these libraries:

1. **date-fns**: A modern JavaScript date utility library
   ```
   npm install date-fns
   ```

2. **Luxon**: A powerful, modern, and friendly wrapper for JavaScript dates and times
   ```
   npm install luxon
   ```

3. **Day.js**: A minimalist JavaScript library for modern browsers with a largely Moment.js-compatible API
   ```
   npm install dayjs
   ```

## Testing

To verify correct timezone handling, test your application with users in different timezones or by changing your system's timezone. Ensure that:

1. Reservation slots are displayed at the correct local time
2. Blocked slots are correctly identified
3. New reservations are created with the correct UTC times

## Specific Example for Available Windows Endpoint

The `ParkingSpotAvailableWindowsView` endpoint (`/parking/parking-spot/<spot_id>/available-windows/`) returns hourly time slots for a specific parking spot, marking each as "available" or "blocked". Here's how to correctly handle the response:

```javascript
// Fetch available windows for a parking spot
const fetchAvailableWindows = async (spotId, date) => {
  const token = localStorage.getItem('token');
  const formattedDate = date.toISOString().split('T')[0]; // Format: YYYY-MM-DD

  const response = await fetch(
    `/parking/parking-spot/${spotId}/available-windows/?date=${formattedDate}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );

  if (response.ok) {
    const windows = await response.json();
    return windows;
  } else {
    throw new Error('Failed to fetch available windows');
  }
};

// Process and display available windows
const displayAvailableWindows = (windows) => {
  return windows.map(window => {
    // Parse the UTC times
    const startTime = new Date(window.start_time);
    const endTime = new Date(window.end_time);

    // Format for display in local timezone
    const formattedStartTime = startTime.toLocaleTimeString('default', {
      hour: '2-digit',
      minute: '2-digit'
    });

    const formattedEndTime = endTime.toLocaleTimeString('default', {
      hour: '2-digit',
      minute: '2-digit'
    });

    return {
      ...window,
      formattedTimeRange: `${formattedStartTime} - ${formattedEndTime}`,
      // Keep the original UTC times for backend operations
      start_time: window.start_time,
      end_time: window.end_time
    };
  });
};

// Example usage
const renderAvailableWindows = async (spotId) => {
  try {
    const today = new Date();
    const windows = await fetchAvailableWindows(spotId, today);
    const processedWindows = displayAvailableWindows(windows);

    // Now you can render these windows in your UI
    processedWindows.forEach(window => {
      console.log(
        `${window.formattedTimeRange}: ${window.status}${window.reason ? ` (${window.reason})` : ''}`
      );
    });
  } catch (error) {
    console.error('Error fetching available windows:', error);
  }
};
```

This example demonstrates how to:
1. Fetch available windows from the backend
2. Parse the UTC times correctly
3. Format the times for display in the user's local timezone
4. Preserve the original UTC times for backend operations

## Conclusion

Proper timezone handling is crucial for the correct functioning of the reservation system. By following these guidelines, you can ensure that reservation slot times are calculated and displayed correctly on the frontend.
