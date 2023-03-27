from django.contrib import admin

from .models import CannedHint, Hint


class HintAdmin(admin.ModelAdmin):

    list_display = (
        "team",
        "puzzle",
        "is_request",
        "timestamp",
        "status",
    )
    list_filter = (
        "status",
        "is_request",
        "puzzle",
        "team",
    )
    search_fields = ("text_content",)


class CannedHintAdmin(admin.ModelAdmin):

    list_display = (
        "puzzle",
        "order",
        "description",
        "keywords",
        "content",
    )
    list_filter = ("puzzle",)
    search_fields = ("content",)


admin.site.register(Hint, HintAdmin)
admin.site.register(CannedHint, CannedHintAdmin)
