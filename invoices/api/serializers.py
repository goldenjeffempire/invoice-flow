from decimal import Decimal
from rest_framework import serializers

from invoices.models import Invoice, LineItem, InvoiceActivity
from invoices.validators import InvoiceBusinessRules


class LineItemSerializer(serializers.ModelSerializer):
    description = serializers.CharField(max_length=500, min_length=1)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("1"))
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = LineItem
        fields = ["id", "description", "quantity", "unit_price", "total"]
        read_only_fields = ["id", "total"]


class InvoiceListSerializer(serializers.ModelSerializer):
    line_items_count = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "client",
            "issue_date",
            "due_date",
            "status",
            "currency",
            "subtotal",
            "total_amount",
            "line_items_count",
            "created_at",
        ]
        read_only_fields = ["id", "invoice_number", "subtotal", "total_amount", "created_at"]
        # Security: account_number removed from list view - sensitive data not exposed in list

    def get_line_items_count(self, obj) -> int:
        return obj.line_items.count()


class InvoiceDetailSerializer(serializers.ModelSerializer):
    items = LineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "client",
            "issue_date",
            "due_date",
            "status",
            "currency",
            "subtotal",
            "tax_total",
            "total_amount",
            "client_memo",
            "internal_notes",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "invoice_number",
            "subtotal",
            "tax_total",
            "total_amount",
            "created_at",
            "updated_at",
        ]


class InvoiceCreateSerializer(serializers.ModelSerializer):
    items = LineItemSerializer(many=True)
    currency = serializers.ChoiceField(choices=Invoice.CURRENCY_CHOICES)

    class Meta:
        model = Invoice
        fields = [
            "client",
            "issue_date",
            "due_date",
            "currency",
            "client_memo",
            "internal_notes",
            "items",
        ]

    def validate_items(self, value):
        return value

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        invoice = Invoice.objects.create(**validated_data)
        for item_data in items_data:
            LineItem.objects.create(invoice=invoice, **item_data)
        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                LineItem.objects.create(invoice=instance, **item_data)

        return instance


class InvoiceStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["draft", "sent", "unpaid", "paid", "overdue"])
    force = serializers.BooleanField(default=False, required=False)


class InvoiceHistorySerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="action", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True, allow_null=True)

    class Meta:
        model = InvoiceActivity
        fields = [
            "id",
            "action",
            "action_display",
            "description",
            "user_email",
            "timestamp",
        ]
        read_only_fields = fields


class InvoiceTemplateSerializer(serializers.Serializer):
    pass
