from django.contrib import admin
from .models import Payment


# Register your models here.
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'payment_id', 'amount', 'status', 'created_at')
    search_fields = ('order_id', 'payment_id')
    list_filter = ('status', 'created_at')