from decimal import Decimal
from rest_framework import serializers

from invoices.models import Invoice, InvoiceTemplate, LineItem


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
            "invoice_id",
            "client_name",
            "client_email",
            "invoice_date",
            "due_date",
            "status",
            "currency",
            "subtotal",
            "total",
            "line_items_count",
            "created_at",
        ]
        read_only_fields = ["id", "invoice_id", "subtotal", "total", "created_at"]
        # Security: account_number removed from list view - sensitive data not exposed in list

    def get_line_items_count(self, obj) -> int:
        return obj.line_items.count()


class InvoiceDetailSerializer(serializers.ModelSerializer):
    line_items = LineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_id",
            "business_name",
            "business_email",
            "business_phone",
            "business_address",
            "client_name",
            "client_email",
            "client_phone",
            "client_address",
            "invoice_date",
            "due_date",
            "status",
            "currency",
            "tax_rate",
            "subtotal",
            "tax_amount",
            "total",
            "notes",
            "line_items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "invoice_id",
            "subtotal",
            "tax_amount",
            "total",
            "created_at",
            "updated_at",
        ]


class InvoiceCreateSerializer(serializers.ModelSerializer):
    line_items = LineItemSerializer(many=True)
    currency = serializers.ChoiceField(choices=Invoice.CURRENCY_CHOICES)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=Decimal("0"), max_value=Decimal("100"))

    class Meta:
        model = Invoice
        fields = [
            "business_name",
            "business_email",
            "business_phone",
            "business_address",
            "client_name",
            "client_email",
            "client_phone",
            "client_address",
            "invoice_date",
            "due_date",
            "currency",
            "tax_rate",
            "notes",
            "line_items",
        ]

    def validate_line_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one line item is required.")
        return value

    def validate(self, attrs):
        if attrs.get("due_date") and attrs.get("invoice_date"):
            if attrs["due_date"] < attrs["invoice_date"]:
                raise serializers.ValidationError("Due date must be after invoice date.")
        return attrs

    def create(self, validated_data):
        line_items_data = validated_data.pop("line_items")
        invoice = Invoice.objects.create(**validated_data)  # type: ignore[attr-defined]
        for item_data in line_items_data:
            LineItem.objects.create(invoice=invoice, **item_data)  # type: ignore[attr-defined]
        return invoice

    def update(self, instance, validated_data):
        line_items_data = validated_data.pop("line_items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if line_items_data is not None:
            instance.line_items.all().delete()
            for item_data in line_items_data:
                LineItem.objects.create(invoice=instance, **item_data)  # type: ignore[attr-defined]

        return instance


class InvoiceStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["paid", "unpaid"])


class InvoiceTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceTemplate
        fields = [
            "id",
            "name",
            "description",
            "business_name",
            "business_email",
            "business_phone",
            "business_address",
            "currency",
            "tax_rate",
            "bank_name",
            "account_name",
            "is_default",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
