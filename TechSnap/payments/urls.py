from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("", views.payment_page, name="payment_page"),
    path("create_order/", views.create_order, name="create_order"),
    path("verify_payment/", views.verify_payment, name="verify_payment"),
    path('update_status/', views.update_status, name='update_status'),  # <-- add this
]
