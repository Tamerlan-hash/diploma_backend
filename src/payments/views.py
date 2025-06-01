from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import PaymentMethod, Transaction, Wallet
from .serializers import PaymentMethodSerializer, TransactionSerializer, WalletSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from decimal import Decimal
from parking.models import Reservation


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing payment methods.
    """
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)

    @swagger_auto_schema(
        operation_description="Set a payment method as default",
        responses={
            200: "Payment method set as default",
            400: "Bad Request",
            404: "Payment method not found"
        }
    )
    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, pk=None):
        payment_method = self.get_object()
        payment_method.is_default = True
        payment_method.save()
        return Response({"status": "Payment method set as default"})


class TransactionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing payment transactions.
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']  # Restrict to GET and POST only

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


class WalletViewSet(viewsets.GenericViewSet):
    """
    API endpoint for managing wallet.
    """
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)

    def get_object(self):
        """Get the user's wallet, creating it if it doesn't exist"""
        try:
            return Wallet.objects.get(user=self.request.user)
        except Wallet.DoesNotExist:
            return Wallet.objects.create(user=self.request.user)

    @swagger_auto_schema(
        operation_description="Get user's wallet information",
        responses={
            200: WalletSerializer(),
        }
    )
    @action(detail=False, methods=['get'])
    def info(self, request):
        """Get the user's wallet information"""
        try:
            wallet = self.get_object()
            serializer = self.get_serializer(wallet)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": f"Error retrieving wallet information: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Get user's wallet transaction history",
        responses={
            200: "Transaction history",
        }
    )
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get the user's wallet transaction history"""
        try:
            wallet = self.get_object()
            transactions = Transaction.objects.filter(wallet=wallet).order_by('-created_at')
            serializer = TransactionSerializer(transactions, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": f"Error retrieving transaction history: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Deposit funds into wallet",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['amount', 'payment_method_id'],
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                'payment_method_id': openapi.Schema(type=openapi.TYPE_STRING),
                'description': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: TransactionSerializer(),
            400: "Bad Request",
            404: "Payment method not found"
        }
    )
    @action(detail=False, methods=['post'])
    def deposit(self, request):
        """Deposit funds into wallet"""
        wallet = self.get_object()

        # Get request data
        amount = request.data.get('amount')
        payment_method_id = request.data.get('payment_method_id')
        description = request.data.get('description', '')

        # Validate required fields
        if not amount or not payment_method_id:
            return Response(
                {"error": "Amount and payment_method_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert amount to Decimal
        try:
            amount = Decimal(amount)
            if amount <= 0:
                return Response(
                    {"error": "Amount must be positive"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid amount"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get payment method
        try:
            payment_method = PaymentMethod.objects.get(id=payment_method_id, user=request.user)
        except PaymentMethod.DoesNotExist:
            return Response(
                {"error": "Payment method not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create deposit transaction
        try:
            transaction = Transaction.create_wallet_deposit(
                wallet=wallet,
                amount=amount,
                description=description,
                payment_method=payment_method
            )
            serializer = TransactionSerializer(transaction)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        operation_description="Withdraw funds from wallet",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['amount'],
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                'description': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: TransactionSerializer(),
            400: "Bad Request"
        }
    )
    @action(detail=False, methods=['post'])
    def withdraw(self, request):
        """Withdraw funds from wallet"""
        wallet = self.get_object()

        # Get request data
        amount = request.data.get('amount')
        description = request.data.get('description', '')

        # Validate required fields
        if not amount:
            return Response(
                {"error": "Amount is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert amount to Decimal
        try:
            amount = Decimal(amount)
            if amount <= 0:
                return Response(
                    {"error": "Amount must be positive"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid amount"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create withdrawal transaction
        try:
            transaction = Transaction.create_wallet_withdrawal(
                wallet=wallet,
                amount=amount,
                description=description
            )
            serializer = TransactionSerializer(transaction)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @swagger_auto_schema(
        operation_description="Make payment using wallet",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['amount'],
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                'reservation_id': openapi.Schema(type=openapi.TYPE_STRING),
                'description': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: TransactionSerializer(),
            400: "Bad Request"
        }
    )
    @action(detail=False, methods=['post'])
    def pay(self, request):
        """Make payment using wallet"""
        wallet = self.get_object()

        # Get request data
        amount = request.data.get('amount')
        reservation_id = request.data.get('reservation_id')
        description = request.data.get('description', '')

        # Validate required fields
        if not amount:
            return Response(
                {"error": "Amount is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate reservation_id
        if not reservation_id:
            return Response(
                {"error": "Reservation ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the reservation
        try:
            reservation = Reservation.objects.get(id=reservation_id, user=request.user)
        except Reservation.DoesNotExist:
            return Response(
                {"error": "Reservation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if reservation is already paid
        if reservation.payment and reservation.payment.status == 'completed':
            return Response(
                {"error": "Reservation is already paid"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert amount to Decimal
        try:
            amount = Decimal(amount)
            if amount <= 0:
                return Response(
                    {"error": "Amount must be positive"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid amount"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process payment using the reservation's wallet payment method
        try:
            success = reservation.process_wallet_payment()
            if not success:
                return Response(
                    {"error": "Payment processing failed. Please check your wallet balance."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get the transaction created by the reservation payment process
            transaction = Transaction.objects.filter(
                wallet=wallet,
                reservation_id=str(reservation.id),
                status='completed'
            ).order_by('-created_at').first()

            if not transaction:
                return Response(
                    {"error": "Transaction not found after payment processing"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            serializer = TransactionSerializer(transaction)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PaymentProcessView(APIView):
    """
    API endpoint for processing payments.
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Process a payment",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['amount', 'payment_method_id', 'reservation_id'],
            properties={
                'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                'payment_method_id': openapi.Schema(type=openapi.TYPE_STRING),
                'reservation_id': openapi.Schema(type=openapi.TYPE_STRING),
                'description': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={
            200: TransactionSerializer(),
            400: "Bad Request",
            404: "Payment method not found or Reservation not found"
        }
    )
    def post(self, request):
        # Get request data
        amount = request.data.get('amount')
        payment_method_id = request.data.get('payment_method_id')
        reservation_id = request.data.get('reservation_id')
        description = request.data.get('description', '')

        # Validate required fields
        if not amount or not payment_method_id:
            return Response(
                {"error": "Amount and payment_method_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate reservation_id
        if not reservation_id:
            return Response(
                {"error": "Reservation ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get payment method
        try:
            payment_method = PaymentMethod.objects.get(id=payment_method_id, user=request.user)
        except PaymentMethod.DoesNotExist:
            return Response(
                {"error": "Payment method not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get the reservation
        try:
            reservation = Reservation.objects.get(id=reservation_id, user=request.user)
        except Reservation.DoesNotExist:
            return Response(
                {"error": "Reservation not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if reservation is already paid
        if reservation.payment and reservation.payment.status == 'completed':
            return Response(
                {"error": "Reservation is already paid"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Process payment using the reservation's card payment method
        try:
            success = reservation.process_card_payment(payment_method.id)
            if not success:
                return Response(
                    {"error": "Payment processing failed"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get the transaction created by the reservation payment process
            transaction = Transaction.objects.filter(
                payment_method=payment_method,
                reservation_id=str(reservation.id),
                status='completed'
            ).order_by('-created_at').first()

            if not transaction:
                return Response(
                    {"error": "Transaction not found after payment processing"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            serializer = TransactionSerializer(transaction)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
