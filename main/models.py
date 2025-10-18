from django.db import models


class WholesaleInquiry(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    company = models.CharField(max_length=255)
    expected_monthly_units = models.PositiveIntegerField()
    message = models.TextField()

    def __str__(self) -> str:
        return self.company
