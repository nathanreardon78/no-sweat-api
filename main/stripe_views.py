import stripe
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .serializers import CheckoutRequestSerializer
from .models import Order
import logging
from django.template.loader import render_to_string
from django.utils import timezone
from .utils.email_service import send_email


logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

SIZE_TO_PRICE = {
    "4 oz": 1499,  # $14.99
    "16 oz": 3499,  # $34.99
    "1 gallon": 14900,  # $149.00
}


@api_view(["POST"])
@permission_classes([AllowAny])
def create_checkout_session(request):
    """
    Create a Stripe Checkout session dynamically using price_data.
    """
    serializer = CheckoutRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    items = serializer.validated_data["items"]

    line_items = []
    for item in items:
        size = item["size"]
        qty = item["quantity"]
        unit_amount = SIZE_TO_PRICE.get(size)
        if unit_amount is None:
            return Response(
                {"error": f"Unsupported size: {size}. Update SIZE_TO_PRICE."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": unit_amount,
                    "product_data": {"name": f"{item['name']} ({size})"},
                },
                "quantity": qty,
            }
        )

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

        # Record in DB
        Order.objects.create(
            session_id=session.id,
            status="pending",
            total_amount=0,
        )

        # Return session URL instead of sessionId
        return Response({"checkoutUrl": session.url}, status=status.HTTP_200_OK)

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
            try:
                full = stripe.checkout.Session.retrieve(
                    session["id"], expand=["payment_intent"]
                )
                amount_cents = full.get("amount_total") or full.get(
                    "payment_intent", {}
                ).get("amount_received")
                if amount_cents is not None:
                    order.total_amount = (amount_cents or 0) / 100.0
            except Exception as e:
                logger.error(f"Error retrieving session details: {e}")
            order.status = "paid"
            order.customer_email = (session.get("customer_details") or {}).get("email")
            order.save()
            
            send_order_confirmation(order, line_items=session.get("line_items", []))

    return Response(status=status.HTTP_200_OK)


def send_order_confirmation(order, items):
    html_body = render_to_string(
        "email_templates/order_confirmation.html",
        {
            "customer_name": order.customer_email.split("@")[0].title(),
            "items": items,
            "total_amount": f"{order.total_amount:.2f}",
            "current_year": timezone.now().year,
        },
    )

    send_email(
        subject="Your No Sweat™ Order Confirmation",
        body_text="Thank you for your order! Your No Sweat™ products are on the way.",
        body_html=html_body,
        recipient=order.customer_email,
    )

