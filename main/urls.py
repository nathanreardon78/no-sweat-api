from django.urls import path
from .views import WholesaleInquiryView
from .stripe_views import create_checkout_session, stripe_webhook


urlpatterns = [
    path('wholesale-inquiry/', WholesaleInquiryView.as_view(), name='wholesale_inquiry'),
    path("create-checkout-session/", create_checkout_session, name="create-checkout-session"),
    path("stripe-webhook/", stripe_webhook, name="stripe-webhook"),
]