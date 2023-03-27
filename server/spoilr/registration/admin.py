from django.contrib import admin

from .models import TeamRegistrationInfo, IndividualRegistrationInfo


def get_fields_except(c, exclude):
    return [f.name for f in c._meta.get_fields() if f.name not in exclude]


@admin.register(TeamRegistrationInfo)
class TeamRegistrationInfoAdmin(admin.ModelAdmin):
    list_display = get_fields_except(
        TeamRegistrationInfo,
        {"id"},
    )
    list_filter = [
        "bg_playstyle",
        "bg_win",
        "tb_room",
        "other_unattached",
        "other_workshop",
        "other_puzzle_club",
        "other_how",
    ]
    search_fields = ("team_name",)


@admin.register(IndividualRegistrationInfo)
class IndividualRegistrationInfoAdmin(admin.ModelAdmin):
    list_display = ["__str__"] + get_fields_except(
        IndividualRegistrationInfo,
        {
            "id",
            "user",
        },
    )
    list_filter = ["bg_playstyle", "bg_under_18", "bg_on_campus"]
    search_fields = ("contact_first_name", "contact_last_name")
