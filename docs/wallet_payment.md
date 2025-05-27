# Wallet Payment for Reservations

This document describes how to use the wallet payment API to pay for parking reservations.

## Overview

The wallet payment API allows users to pay for parking reservations using their wallet balance. This is a convenient way to pay for reservations without having to enter payment details each time.

## API Endpoints

### Create Payment

Before making a payment, you need to create a payment for the reservation.

**URL**: `/parking/reservations/{reservation_id}/payment/create/`

**Method**: `POST`

**Authentication**: Required

**Response**:
```json
{
  "id": 1,
  "amount": "200.00",
  "status": "pending",
  "payment_date": null,
  "payment_method": "",
  "transaction_id": "",
  "created_at": "2023-06-01T12:00:00Z",
  "updated_at": "2023-06-01T12:00:00Z"
}
```

### Pay with Wallet

After creating a payment, you can pay for the reservation using your wallet balance.

**URL**: `/parking/reservations/{reservation_id}/payment/wallet/`

**Method**: `POST`

**Authentication**: Required

**Response**:
```json
{
  "id": 1,
  "amount": "200.00",
  "status": "completed",
  "payment_date": "2023-06-01T12:05:00Z",
  "payment_method": "wallet",
  "transaction_id": "WPAYMENT-123",
  "created_at": "2023-06-01T12:00:00Z",
  "updated_at": "2023-06-01T12:05:00Z"
}
```

**Error Responses**:

- `404 Not Found`: Wallet not found
- `400 Bad Request`: Insufficient funds
- `400 Bad Request`: Payment already completed

## Usage Example

Here's an example of how to use the wallet payment API:

```javascript
// Create payment
const createPaymentResponse = await fetch(`/parking/reservations/123/payment/create/`, {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer <token>',
    'Content-Type': 'application/json'
  }
});

// Pay with wallet
const walletPaymentResponse = await fetch(`/parking/reservations/123/payment/wallet/`, {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer <token>',
    'Content-Type': 'application/json'
  }
});

const paymentResult = await walletPaymentResponse.json();
console.log(paymentResult);
```

## Notes

- The user must have sufficient funds in their wallet to make a payment.
- If the payment is already completed, the API will return an error.
- After successful payment, the reservation payment status will be updated to "completed".