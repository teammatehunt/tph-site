from django.contrib import admin

from pwreset.models import Token


# Register your models here.
class TokenAdmin(admin.ModelAdmin):
    list_display = ("user", "token", "expiry")


admin.site.register(Token, TokenAdmin)
