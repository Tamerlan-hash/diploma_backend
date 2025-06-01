# Sensor API Tests

This document describes the test cases for the Sensor API endpoints.

## Overview

The tests are designed to verify the functionality of two API endpoints:

1. `POST /api/sensor/sensor/update/`: For sensors to update their occupation status.
2. `GET /api/sensor/blocker/status/<reference>/`: For blockers to check their status.

## Test Cases

### SensorUpdateAPIView Tests

The `TestSensorUpdateAPI` class contains the following test cases:

1. `test_sensor_update_success`: Tests that a sensor can successfully update its occupation status.
   - Creates a test parking spot and sensor
   - Sends a POST request to update the sensor's occupation status
   - Verifies that the response status code is 200 OK
   - Verifies that the response data shows the updated occupation status
   - Verifies that the sensor's occupation status is updated in the database

2. `test_sensor_update_invalid_reference`: Tests the behavior when an invalid sensor reference is provided.
   - Sends a POST request with a non-existent sensor reference
   - Verifies that the response status code is 404 Not Found

3. `test_sensor_update_missing_reference`: Tests the behavior when the sensor reference is missing from the request.
   - Sends a POST request without a sensor reference
   - Verifies that the response status code is 400 Bad Request

### BlockerStatusAPIView Tests

The `TestBlockerStatusAPI` class contains the following test cases:

1. `test_blocker_status_success`: Tests that a blocker can successfully retrieve its status.
   - Creates a test parking spot and blocker
   - Sends a GET request to retrieve the blocker's status
   - Verifies that the response status code is 200 OK
   - Verifies that the response data contains the correct blocker reference
   - Verifies that the response data shows the correct blocker status

2. `test_blocker_status_invalid_reference`: Tests the behavior when an invalid blocker reference is provided.
   - Sends a GET request with a non-existent blocker reference
   - Verifies that the response status code is 404 Not Found

## Running the Tests

To run the tests, use the following command from the project root directory:

```bash
python -m pytest tests/test_sensor_api.py -v
```

The `-v` flag enables verbose output, showing the result of each test case.