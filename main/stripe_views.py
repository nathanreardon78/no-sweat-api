import stripe
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Order

# Use your Stripe secret key from environment variables
stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(["POST"])
def create_checkout_session(request):
    """
    Create a Stripe checkout session for given cart items.
    Expects: { "items": [{ "name": "No Sweat", "quantity": 2, "price": 19.99 }] }
    """
    try:
        data = request.data
        line_items = []

        for item in data.get("items", []):
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": item["name"]},
                    "unit_amount": int(float(item["price"]) * 100),
                },
                "quantity": item["quantity"],
            })

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url="https://nosweatsealer.com/success",
            cancel_url="https://nosweatsealer.com/cancel",
        )

        # Save order
        total = sum([float(i["price"]) * i["quantity"] for i in data["items"]])
        Order.objects.create(session_id=session.id, total_amount=total)

        return Response({"sessionId": session.id})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def stripe_webhook(request):
    """
    Stripe webhook to confirm successful payment.
    """
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
            order.status = "paid"
            order.customer_email = session.get("customer_details", {}).get("email", "")
            order.save()

    return Response(status=status.HTTP_200_OK)
