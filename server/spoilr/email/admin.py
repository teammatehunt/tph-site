from django.contrib import admin

from .models import BadEmailAddress, CannedEmail, Email, EmailTemplate


class EmailAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "from_address",
        "to_addresses",
        "cc_and_bcc_len",
        "team",
        "date",
        "status",
        "task",
    )
    list_filter = ("status", "team")
    search_fields = ("from_address", "to_addresses", "cc_addresses", "bcc_addresses")
    readonly_fields = ("raw_content_",)

    def raw_content_(self, obj):
        return str(obj.raw_content, "utf-8", "backslashreplace")

    def cc_and_bcc_len(self, obj):
        return len(obj.cc_addresses) + len(obj.bcc_addresses)

    cc_and_bcc_len.short_description = "CC+BCC"

    def date(self, obj):
        return obj.received_datetime

    date.admin_order_field = "received_datetime"


class BadEmailAddressAdmin(admin.ModelAdmin):
    list_display = ("email", "reason")
    list_filter = ("reason",)


class CannedEmailAdmin(admin.ModelAdmin):
    list_display = ("slug", "description", "subject", "interaction")
    list_filter = ("interaction",)
    search_fields = ("slug", "subject", "text_content", "description")


admin.site.register(Email, EmailAdmin)
admin.site.register(EmailTemplate)
admin.site.register(BadEmailAddress, BadEmailAddressAdmin)
admin.site.register(CannedEmail, CannedEmailAdmin)
