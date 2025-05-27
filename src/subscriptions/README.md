# Tariff System

## Overview

The tariff system allows setting different prices for parking spots based on various factors:
- Location (zone)
- Specific parking spot
- Time of day
- Day of week
- Special periods (holidays, etc.)

## Setting Tariffs for Specific Parking Spots

You can set tariffs for specific parking spots in two ways:

### 1. Using the Admin Interface

1. Go to the Django admin interface (`/admin/`)
2. Navigate to "Subscriptions" > "Tariff rules"
3. Click "Add Tariff rule"
4. Fill in the required fields:
   - Name: A descriptive name for the rule
   - Zone: The zone this rule applies to
   - Parking spot: Select a specific parking spot (leave empty for zone-wide rules)
   - Price per hour: The hourly rate for this rule
   - Priority: Higher priority rules override lower priority ones
   - Time period: When this rule applies (all day, morning, afternoon, evening, night, or custom)
   - Day type: What days this rule applies to (all days, weekdays, weekends, holidays, or custom)
5. Click "Save"

### 2. Using the API

Administrators can use the API to manage tariff rules:

```
POST /api/subscriptions/admin/rules/
{
  "name": "Special Rate for Spot A1",
  "zone": 1,
  "parking_spot": "A1-reference-id",
  "price_per_hour": 500,
  "priority": 100,
  "time_period": "all_day",
  "day_type": "all"
}
```

## How Tariffs are Applied

When calculating the price for a parking reservation:

1. The system first checks for spot-specific tariff rules that apply to the exact parking spot being reserved.
2. If no spot-specific rules are found or none are applicable for the given time, it falls back to zone-wide rules.
3. Within each category (spot-specific or zone), the rule with the highest priority is selected.
4. If no rules are found at all, a default price is used.

This ensures that you can set special rates for specific parking spots that override the general zone rates.

## Testing Tariff Rules

You can use the `calculate_price` management command to test how tariff rules are applied:

```
python manage.py calculate_price --user_id=1 --spot_id=A1 --start_time="2023-06-01 10:00" --duration=2
```

This will show you the calculated price and which tariff rules were applied.

## Subscription Discounts

If a user has an active subscription, their subscription discount is applied to the tariff price. For example, if a parking spot costs 500 tenge per hour and the user has a subscription with a 10% discount, they will pay 450 tenge per hour.