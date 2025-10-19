from django.db import models


class WholesaleInquiry(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    company = models.CharField(max_length=255)
    expected_monthly_units = models.PositiveIntegerField()
    message = models.TextField()

    def __str__(self) -> str:
        return self.company


class Order(models.Model):
    session_id = models.CharField(max_length=255, unique=True)
    customer_email = models.EmailField(blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.status}"
