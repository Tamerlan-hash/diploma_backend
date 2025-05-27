from rest_framework import serializers
from .models import PaymentMethod, Transaction, Wallet


class PaymentMethodSerializer(serializers.ModelSerializer):
    card_number_masked = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethod
        fields = ['id', 'type', 'card_number', 'card_number_masked', 'expiry_date', 'cardholder_name', 'is_default', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'card_number': {'write_only': True},  # Don't expose full card number in responses
        }

    def get_card_number_masked(self, obj):
        # Return only the last 4 digits of the card number
        return f"**** **** **** {obj.card_number[-4:]}"

    def create(self, validated_data):
        # Set the user to the current user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    payment_method_details = serializers.SerializerMethodField()
    wallet_details = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'payment_method', 'payment_method_details', 
            'wallet', 'wallet_details', 'transaction_type',
            'amount', 'status', 'reservation_id', 'description', 
            'transaction_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'transaction_id', 'created_at', 'updated_at']

    def get_payment_method_details(self, obj):
        if obj.payment_method:
            return {
                'id': obj.payment_method.id,
                'type': obj.payment_method.type,
                'card_number_masked': f"**** **** **** {obj.payment_method.card_number[-4:]}",
            }
        return None

    def get_wallet_details(self, obj):
        if obj.wallet:
            return {
                'id': obj.wallet.id,
                'balance': obj.wallet.balance,
            }
        return None

    def create(self, validated_data):
        # Set the user to the current user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class WalletSerializer(serializers.ModelSerializer):
    transactions = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'created_at', 'updated_at', 'transactions']
        read_only_fields = ['id', 'balance', 'created_at', 'updated_at', 'transactions']

    def get_transactions(self, obj):
        # Get the 5 most recent transactions
        recent_transactions = obj.transactions.all().order_by('-created_at')[:5]
        return TransactionSerializer(recent_transactions, many=True).data
