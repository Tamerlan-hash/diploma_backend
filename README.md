# Diploma Smart Parking Backend

## Reservation Flow

The system implements the following reservation flow:

1. User registers and logs in to the application
2. User selects a parking spot on the map
3. User initiates a reservation by clicking "Reserve"
4. User completes payment (via bank card or wallet balance)
5. After successful payment, the parking blocker is raised and waits for the user
6. User arrives at the parking spot and lowers the blocker through the application
7. User parks their car
8. When the reservation time is about to expire, the user receives a notification
9. User can extend the reservation if the spot is not reserved by another user

## Payment Options

The system supports two payment methods:

1. **Bank Card Payment**: User can add and use bank cards for payments
2. **Wallet Balance**: User can deposit money to their wallet and use it for payments

## Notifications

The system sends notifications to users in the following cases:

1. When a reservation is about to expire (30 minutes before)
   - If the spot is available for extension, the notification includes this option
   - If another user has reserved the spot, the notification informs about this
2. When a payment is successful
3. When a reservation is extended

## Implementation Details

### Models

- **Reservation**: Manages parking spot reservations
- **Payment**: Tracks payments for reservations
- **Transaction**: Records financial transactions (card payments, wallet deposits/withdrawals)
- **Wallet**: Manages user wallet balances
- **PaymentMethod**: Stores user payment methods (credit/debit cards)
- **Blocker**: Controls physical parking blockers
- **Notification**: Stores user notifications

### Key Features

- **User Arrival**: When a user arrives, they can lower the blocker through the app
- **Reservation Extension**: Users can extend active reservations if the spot is available
- **Expiration Notifications**: System automatically notifies users about expiring reservations
- **Multiple Payment Options**: Support for both card payments and wallet balance

## Setup and Configuration

1. Make sure to run migrations to create the necessary database tables:
   ```
   python manage.py makemigrations
   python manage.py migrate
   ```

2. Set up a task scheduler (like Celery) to run the following tasks periodically:
   - `parking.tasks.check_expiring_reservations`: Sends notifications for reservations about to expire
   - `parking.tasks.auto_complete_expired_reservations`: Automatically completes expired reservations