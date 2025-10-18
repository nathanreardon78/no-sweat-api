from decouple import config
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.template.loader import render_to_string
from datetime import datetime
from .utils.email_service import send_email


class WholesaleInquiryView(APIView):
    def post(self, request):
        name = request.data.get("name")
        email = request.data.get("email")
        company = request.data.get("company")
        expected_units = request.data.get("expected_units")
        message = request.data.get("message")

        html_admin = render_to_string(
            "emails/wholesale_template.html",
            {
                "name": name,
                "email": email,
                "company": company,
                "expected_units": expected_units,
                "year": datetime.now().year,
            },
        )
        send_email(
            subject="New Wholesale Inquiry - No Sweat™",
            body_text=f"New inquiry from {name} ({email})",
            body_html=html_admin,
            recipient=config("SES_RECEIVER"),
        )

        html_customer = render_to_string(
            "emails/wholesale_confirmation.html",
            {"name": name, "year": datetime.now().year},
        )
        send_email(
            subject="Thank You for Your Inquiry - No Sweat™",
            body_text="Thank you for contacting No Sweat™. Our team will reply soon.",
            body_html=html_customer,
            recipient=email,
        )
        return Response(
            {"message": "Inquiry sent successfully"}, status=status.HTTP_200_OK
        )
