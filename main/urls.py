from django.urls import path
from .views import WholesaleInquiryView


urlpatterns = [
    path('wholesale-inquiry/', WholesaleInquiryView.as_view(), name='wholesale_inquiry'),
]

