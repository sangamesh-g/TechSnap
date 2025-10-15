import json
import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from organizations.models import Invite
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import Payment

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def payment_page(request):
    payments = Payment.objects.all()
    return render(request, "payments/payment_page.html", {
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "payments": payments
    })


@csrf_exempt
def create_order(request):
    if request.method == "POST":
        amount = int(request.POST.get("amount", 0))
        if amount < 1:
            return JsonResponse({"error": "Amount must be at least 1 INR"}, status=400)

        currency = "INR"
        try:
            # Razorpay expects amount in paise (multiply by 100)
            order = client.order.create({
                "amount": amount * 100,  # convert rupees to paise
                "currency": currency,
                "payment_capture": 1
            })
            return JsonResponse(order)
        except razorpay.errors.BadRequestError as e:
            return JsonResponse({"error": str(e)}, status=400)
        
        
@csrf_exempt
def verify_payment(request):
    if request.method != "POST":
        return JsonResponse({"status": "Invalid request method"}, status=400)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "Invalid JSON"}, status=400)

    try:
        # Verify Razorpay signature
        client.utility.verify_payment_signature({
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        })

        payment = Payment.objects.get(order_id=data['razorpay_order_id'])
        payment.payment_id = data['razorpay_payment_id']
        payment.signature = data['razorpay_signature']
        payment.status = "paid"
        payment.save()

        return JsonResponse({"status": "Payment Successful"})

    except razorpay.errors.SignatureVerificationError:
        payment = Payment.objects.get(order_id=data['razorpay_order_id'])
        payment.status = "failed"
        payment.save()
        return JsonResponse({"status": "Payment Verification Failed"})



def update_status(request):
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        order_id = data.get("order_id")
        status = data.get("status")
        reason = data.get("reason", "")

        try:
            payment = Payment.objects.get(order_id=order_id)
            payment.status = status
            if reason:
                payment.failure_reason = reason
            payment.save()
            return JsonResponse({"status": "updated"})
        except Payment.DoesNotExist:
            return JsonResponse({"status": "order not found"}, status=404)
    return JsonResponse({"status": "invalid request"}, status=400)

import uuid


client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@login_required
def process_payment(request, token):
    """
    Step 1: Create a Razorpay order for ₹500 when accepting an invite.
    Step 2: Redirect user to payment page.
    Step 3: Verify payment via webhook or frontend callback.
    """
    invite = get_object_or_404(
        Invite,
        token=token,
        accepted=False,
        expires_at__gt=timezone.now()
    )

    amount_inr = 500
    amount_paise = amount_inr * 100

    # 1️⃣ Create a Razorpay order
    razorpay_order = client.order.create({
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1,  # auto-capture
        "notes": {"invite_id": str(invite.id), "user": str(request.user.id)}
    })

    # 2️⃣ Create Payment entry in DB
    payment = Payment.objects.create(
        user=request.user,
        order_id=razorpay_order["id"],
        amount=amount_paise,
        status="created"
    )

    # Link payment to invite
    invite.payment = payment
    invite.save(update_fields=["payment"])

    # 3️⃣ Render Razorpay checkout page
    context = {
        "invite": invite,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": amount_inr,
        "order_id": razorpay_order["id"],
        "user_email": request.user.email,
        "user_name": request.user.get_full_name() or request.user.username,
        "callback_url": "/payments/verify/",
    }
    return render(request, "payments/process_payment.html", context)