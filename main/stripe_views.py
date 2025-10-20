import os
import json
import stripe
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .serializers import CheckoutRequestSerializer
from .models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY

# Map your sizes to Stripe Price IDs (set in environment). Example keys:
# STRIPE_PRICE_4OZ, STRIPE_PRICE_16OZ, STRIPE_PRICE_1GAL
SIZE_TO_PRICE_ID = {
    "4 oz": 14.99,
    "16 oz": 34.99,
    "1 gallon": 149.00
}


@api_view(["POST"])
@permission_classes([AllowAny])
def create_checkout_session(request):
    """
    Body:
    {
      "items": [
        {"name": "No Sweat™", "size": "4 oz", "quantity": 2},
        {"name": "No Sweat™", "size": "16 oz", "quantity": 1}
      ]
    }
    """
    print(request.data)
    serializer = CheckoutRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    items = serializer.validated_data["items"]
    print("Creating checkout session for items:", items)

    line_items = []
    for item in items:
        size = item["size"]
        qty = item["quantity"]
        price_id = SIZE_TO_PRICE_ID.get(size)
        if not price_id:
            return Response(
                {"error": f"Unsupported size: {size}. Please update SIZE_TO_PRICE_ID."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        line_items.append({"price": price_id, "quantity": qty})

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=line_items,
            allow_promotion_codes=True,
            success_url="https://nosweatsealer.com/success",
            cancel_url="https://nosweatsealer.com/cancel",
            automatic_tax={"enabled": False},
        )

        # Create a placeholder Order record (amount will be finalized via webhook)
        Order.objects.create(
            session_id=session.id,
            status="pending",
            total_amount=0,
            currency="usd",
        )

        return Response({"sessionId": session.id}, status=status.HTTP_200_OK)
    except stripe.StripeError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order = Order.objects.filter(session_id=session["id"]).first()
        if order:
            # If you enabled 'expand' or retrieve the session again, you can get amount_total.
            try:
                full = stripe.checkout.Session.retrieve(
                    session["id"], expand=["payment_intent"]
                )
                amount_cents = full.get("amount_total") or full.get(
                    "payment_intent", {}
                ).get("amount_received")
                if amount_cents is not None:
                    order.total_amount = (amount_cents or 0) / 100.0
            except Exception:
                pass
            order.status = "paid"
            order.customer_email = (session.get("customer_details") or {}).get("email")
            order.save()

    return Response(status=status.HTTP_200_OK)
