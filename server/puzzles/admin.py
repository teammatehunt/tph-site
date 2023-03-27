from django import forms
from django.contrib import admin
from django.db import transaction
from django.urls import reverse
from spoilr.core.models import PseudoAnswer
from spoilr.hints.models import CannedHint

from puzzles.models import (
    CustomPuzzleSubmission,
    DeepFloor,
    ExtraGuessGrant,
    ExtraUnlock,
    Feedback,
    Minipuzzle,
    Puzzle,
    PuzzleAccess,
    PuzzleSubmission,
    Survey,
    Team,
)
from puzzles.models.interactive import PuzzleAction, PuzzleState, Session, UserState
from puzzles.models.story import StoryCard, StoryCardAccess, StoryState


class PseudoAnswerInline(admin.TabularInline):
    model = PseudoAnswer


class CannedHintInline(admin.TabularInline):
    model = CannedHint


class PuzzleAdmin(admin.ModelAdmin):
    inlines = [PseudoAnswerInline, CannedHintInline]
    ordering = ("round__order", "deep", "name")
    list_display = (
        "name",
        "slug",
        "round",
        "deep",
        "emoji",
        "is_meta",
    )
    list_filter = ("is_meta", "round")
    search_fields = ("name", "slug", "id", "round__name", "round__slug")

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        overrides = ("override_hint_unlocked", "override_virtual_unlocked")
        return [
            (
                "Overrides",
                {"fields": overrides},
            ),
            (
                "Metadata",
                {
                    "fields": [
                        field
                        for field in fieldsets[0][1]["fields"]
                        if field not in overrides
                    ]
                },
            ),
        ]

    def view_on_site(self, obj):
        return obj.url


class TeamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "creation_time",
        "is_prerelease_testsolver_short",
        "is_hidden",
    )
    list_filter = ("is_prerelease_testsolver", "is_hidden")
    search_fields = ("name",)

    # You can't sort by this column but meh.
    def is_prerelease_testsolver_short(self, obj):
        return obj.is_prerelease_testsolver

    is_prerelease_testsolver_short.short_description = "Prerel.?"
    is_prerelease_testsolver_short.boolean = True


class PuzzleAccessAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle", "timestamp")
    list_filter = ("puzzle", "team")
    autocomplete_fields = ("puzzle",)


class PuzzleSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "team",
        "puzzle",
        "answer",
        "timestamp",
        "correct",
        "used_free_answer",
    )
    list_filter = ("correct", "used_free_answer", "puzzle", "team")
    search_fields = ("team__name", "puzzle__slug", "answer")
    autocomplete_fields = ("team", "puzzle")


class ExtraGuessGrantAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle", "status", "extra_guesses")
    list_filter = ("puzzle", "team")


class SurveyAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle")
    list_filter = ("puzzle", "team")
    search_fields = ("comments",)


class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle")
    list_filter = ("puzzle", "team")
    search_fields = ("comments",)


class MinipuzzleAdmin(admin.ModelAdmin):
    list_display = (
        "team",
        "puzzle",
        "ref",
        "solved",
        "create_time",
        "solved_time",
    )
    list_filter = ("team", "puzzle", "ref", "solved")
    autocomplete_fields = ("team", "puzzle")


class CustomSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "raw_answer",
        "team",
        "puzzle",
        "minipuzzle",
        "correct",
        "count",
    )
    list_filter = ("team", "puzzle", "minipuzzle", "correct")
    autocomplete_fields = ("team", "puzzle")


class PuzzleActionAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle", "subpuzzle", "action", "datetime")
    list_filter = ("team", "puzzle", "subpuzzle", "action")
    autocomplete_fields = ("team", "puzzle")


class PuzzleStateAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle")
    list_filter = ("team", "puzzle")
    autocomplete_fields = ("team", "puzzle")


class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "team",
        "puzzle",
        "storycard",
        "start_time",
        "finish_time",
        "is_complete",
    )
    list_filter = (
        "team",
        "puzzle",
        "storycard",
        "start_time",
        "finish_time",
        "is_complete",
    )
    autocomplete_fields = ("team", "puzzle", "storycard")


class StoryCardAdmin(admin.ModelAdmin):
    list_display = ("slug", "order", "act", "title", "text", "puzzle")
    list_filter = ("slug", "text")
    search_fields = ("slug", "title")
    autocomplete_fields = ("puzzle",)


class StoryCardAccessAdmin(admin.ModelAdmin):
    list_display = ("team", "story_card", "timestamp")
    list_filter = ("story_card", "team")
    autocomplete_fields = ("story_card", "team")


class StoryStateAdmin(admin.ModelAdmin):
    list_display = ("team", "state")
    list_filter = ("team", "state")
    autocomplete_fields = ("team",)


class UserStateAdmin(admin.ModelAdmin):
    list_display = ("team", "puzzle", "uuid")
    list_filter = ("team", "puzzle", "uuid")
    autocomplete_fields = ("team", "puzzle")


class DeepFloorAdmin(admin.ModelAdmin):
    list_display = ("team", "timestamp", "enabled", "deep_key", "min_deep")
    list_filter = ("team", "enabled", "deep_key")
    autocomplete_fields = ("team",)


class ExtraUnlockAdmin(admin.ModelAdmin):
    list_display = ("team", "deep_key", "count")
    list_filter = ("team", "deep_key")
    autocomplete_fields = ("team",)


admin.site.register(CustomPuzzleSubmission, CustomSubmissionAdmin)
admin.site.register(DeepFloor, DeepFloorAdmin)
admin.site.register(ExtraGuessGrant, ExtraGuessGrantAdmin)
admin.site.register(ExtraUnlock, ExtraUnlockAdmin)
admin.site.register(Puzzle, PuzzleAdmin)
admin.site.register(PuzzleAccess, PuzzleAccessAdmin)
admin.site.register(PuzzleSubmission, PuzzleSubmissionAdmin)
admin.site.register(Minipuzzle, MinipuzzleAdmin)
admin.site.register(Survey, SurveyAdmin)
admin.site.register(Feedback, FeedbackAdmin)
admin.site.register(PuzzleAction, PuzzleActionAdmin)
admin.site.register(PuzzleState, PuzzleStateAdmin)
admin.site.register(UserState, UserStateAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(StoryCard, StoryCardAdmin)
admin.site.register(StoryCardAccess, StoryCardAccessAdmin)
admin.site.register(StoryState, StoryStateAdmin)
admin.site.register(Team, TeamAdmin)
