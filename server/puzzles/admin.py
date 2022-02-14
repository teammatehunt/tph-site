from django import forms
from django.contrib import admin
from django.db import transaction
from django.urls import reverse

from puzzles.models import (
    AnswerSubmission,
    BadEmailAddress,
    CustomPuzzleSubmission,
    Email,
    EmailTemplate,
    Errata,
    ExtraGuessGrant,
    Hint,
    Puzzle,
    PuzzleMessage,
    PuzzleUnlock,
    StoryCard,
    StoryCardUnlock,
    Survey,
    Team,
    TeamMember,
)
from puzzles.models.interactive import PuzzleAction, PuzzleState


class PuzzleMessageInline(admin.TabularInline):
    model = PuzzleMessage


class PuzzleAdmin(admin.ModelAdmin):
    inlines = [PuzzleMessageInline]
    ordering = ("deep", "name")
    list_display = (
        "name",
        "slug",
        "round",
        "deep",
        "metameta_deep",
        "emoji",
        "is_meta",
    )
    list_filter = ("is_meta", "round")

    def view_on_site(self, obj):
        return f"/puzzles/{obj.slug}"


class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "team")
    list_filter = ("team",)
    search_fields = ("name", "email")


class TeamMemberInline(admin.TabularInline):
    model = TeamMember


class TeamAdmin(admin.ModelAdmin):
    inlines = [TeamMemberInline]
    list_display = (
        "team_name",
        "slug",
        "creation_time",
        "is_prerelease_testsolver_short",
        "is_hidden",
    )
    list_filter = ("is_prerelease_testsolver", "is_hidden")
    search_fields = ("team_name",)

    # You can't sort by this column but meh.
    def is_prerelease_testsolver_short(self, obj):
        return obj.is_prerelease_testsolver

    is_prerelease_testsolver_short.short_description = "Prerel.?"
    is_prerelease_testsolver_short.boolean = True

    def view_on_site(self, obj):
        return obj.team_url


class PuzzleUnlockAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle", "unlock_datetime")
    list_filter = ("puzzle", "team")


class AnswerSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "team",
        "puzzle",
        "submitted_answer",
        "submitted_datetime",
        "is_correct",
        "used_free_answer",
    )
    list_filter = ("is_correct", "used_free_answer", "puzzle", "team")
    search_fields = ("submitted_answer",)


class ExtraGuessGrantAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle", "status", "extra_guesses")
    list_filter = ("puzzle", "team")


class SurveyAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle")
    list_filter = ("puzzle", "team")
    search_fields = ("comments",)


class BadEmailAddressAdmin(admin.ModelAdmin):
    list_display = ("email", "reason")
    list_filter = ("reason",)


class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "scheduled_datetime",
        "subject",
        "from_address",
        "status",
    )
    list_filter = ("from_address", "status")


class EmailAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "from_address",
        "to_addresses",
        "cc_and_bcc_len",
        "team",
        "date",
        "status",
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


class HintAdmin(admin.ModelAdmin):
    def view_on_site(self, obj):
        return reverse("hint", args=(obj.id,))

    list_display = (
        "team",
        "puzzle",
        "is_request",
        "submitted_datetime",
        "claimer",
        "claimed_datetime",
        "status",
        # "answered_datetime",
    )
    list_filter = (
        "status",
        "is_request",
        "claimed_datetime",
        # "answered_datetime",
        "puzzle",
        "team",
        "claimer",
    )
    search_fields = ("text_content",)


class StoryCardAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "text",
        "deep",
        "unlock_order",
        "min_main_round_solves",
    )
    list_filter = ("slug", "deep")
    ordering = ("deep", "unlock_order", "slug")


class StoryCardUnlockAdmin(admin.ModelAdmin):
    list_display = ("team", "story_card", "unlock_datetime")
    list_filter = ("story_card", "team")


class ErrataAdmin(admin.ModelAdmin):
    list_display = ("puzzle", "text", "creation_time")
    list_filter = ("puzzle",)


class CustomSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "submission",
        "team",
        "puzzle",
        "subpuzzle",
        "is_correct",
        "count",
    )
    list_filter = ("team", "puzzle", "subpuzzle", "is_correct")


class PuzzleActionAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle", "action", "datetime")
    list_filter = ("team", "puzzle", "action")


class PuzzleStateAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle")
    list_filter = ("team", "puzzle")


admin.site.register(Puzzle, PuzzleAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(TeamMember, TeamMemberAdmin)
admin.site.register(PuzzleUnlock, PuzzleUnlockAdmin)
admin.site.register(AnswerSubmission, AnswerSubmissionAdmin)
admin.site.register(CustomPuzzleSubmission, CustomSubmissionAdmin)
admin.site.register(ExtraGuessGrant, ExtraGuessGrantAdmin)
admin.site.register(Survey, SurveyAdmin)
admin.site.register(BadEmailAddress, BadEmailAddressAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(Email, EmailAdmin)
admin.site.register(Hint, HintAdmin)
admin.site.register(StoryCard, StoryCardAdmin)
admin.site.register(StoryCardUnlock, StoryCardUnlockAdmin)
admin.site.register(Errata, ErrataAdmin)
admin.site.register(PuzzleAction, PuzzleActionAdmin)
admin.site.register(PuzzleState, PuzzleStateAdmin)
