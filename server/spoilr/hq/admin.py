from django.contrib import admin

from .models import Handler, HqLog, Task


class TaskAdmin(admin.ModelAdmin):

    list_display = (
        "__str__",
        "handler",
        "status",
    )
    list_filter = (
        "status",
        "handler",
    )


admin.site.register(Handler)
admin.site.register(HqLog)
admin.site.register(Task, TaskAdmin)
