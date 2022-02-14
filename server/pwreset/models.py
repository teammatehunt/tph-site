from django.contrib.auth.models import User
from django.db import models


class Token(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100)
    expiry = models.DateTimeField()
