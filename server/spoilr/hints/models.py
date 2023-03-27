import email

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Q
from django.template.loader import render_to_string
from spoilr.core.models import Puzzle, Team
from spoilr.email.models import Email
from spoilr.hq.models import Task, TaskStatus
from spoilr.utils import generate_url


class Hint(models.Model):
    """Same model for a hint request or a hint response."""

    NO_RESPONSE = "NR"
    ANSWERED = "ANS"
    REQUESTED_MORE_INFO = "MOR"
    REFUNDED = "REF"
    OBSOLETE = "OBS"
    RESOLVED = "RES"

    STATUSES = {
        NO_RESPONSE: "No response",
        ANSWERED: "Answered",
        REQUESTED_MORE_INFO: "Request more info",  # we asked the team for more info
        REFUNDED: "Refund",  # we can't answer for some reason. refund
        OBSOLETE: "Obsolete",  # puzzle was solved while waiting for hint
        RESOLVED: "Resolved without response",  # requesters are not expecting an additional reply
    }

    HINT_EMAIL_ADDRESS = f"hints@{settings.EMAIL_USER_DOMAIN}"
    CONTACT_EMAIL_ADDRESS = f"contact@{settings.EMAIL_USER_DOMAIN}"

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    puzzle = models.ForeignKey(Puzzle, on_delete=models.CASCADE)
    root_ancestor_request = models.ForeignKey(
        "self",
        related_name="hint_thread_set",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )  # field is null if hint is the original request
    is_request = models.BooleanField(default=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    text_content = models.TextField(blank=True)
    notify_emails = models.TextField(default="none")
    email = models.OneToOneField(
        Email, on_delete=models.SET_NULL, null=True, blank=True
    )

    tasks = GenericRelation(Task, related_query_name="task")

    response = models.ForeignKey(
        "self",
        related_name="request_set",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    # Status for original hint of thread determines status of whole thread.
    # Individual statuses OBSOLETE and RESOLVED will also resolve a request
    # that doesn't have a response associated with it, but most followup hints
    # should have the status NO_RESPONSE because their status is tracked by the
    # original hint.
    status = models.CharField(
        choices=tuple(STATUSES.items()), default=NO_RESPONSE, max_length=3
    )

    def get_or_populate_response(self):
        "Get the response object for a hint request or create an empty unsaved one."
        if not self.is_request:
            raise ValueError("Hint responding to is not a request")
        if self.response is not None:
            response = self.response
        else:
            # keep this list up to date with views.puzzles.hint()
            response = Hint(
                team=self.team,
                puzzle=self.puzzle,
                root_ancestor_request_id=self.original_request_id,
                is_request=False,
                notify_emails=self.notify_emails,
            )
        response.status = self.original_request.status
        return response

    def get_prior_requests_needing_response(self):
        "Get unanswered hint requests in the same thread."
        return list(
            Hint.objects.filter(
                self.original_request_filter(),
                timestamp__lte=self.timestamp,
                is_request=True,
                response__isnull=True,
            ).exclude(status__in=(Hint.OBSOLETE, Hint.RESOLVED))
        )

    def populate_response_and_update_requests(self, text_content, status=None):
        """
        Create empty hint response object. Returns {
            response: Hint, # response hint
            requests: List[Hint], # list of requests whose response need to be updated
            response_email: Email, # response email to be sent (can be None if no email)
        }
        These objects are not yet saved when returned.
        """
        requests = self.get_prior_requests_needing_response()
        reply_to = (
            Hint.objects.filter(
                self.original_request_filter(),
                timestamp__lte=self.timestamp,
                email__isnull=False,
            )
            .select_related("email")
            .last()
        )
        reply_to_email = reply_to.email if reply_to else None

        response = Hint(
            team=self.team,
            puzzle=self.puzzle,
            root_ancestor_request_id=self.original_request_id,
            is_request=False,
            text_content=text_content,
            status=status,
        )

        notify_emails = "none"

        for request in requests:
            request.response = response

            if request.notify_emails == "none":
                pass
            elif request.notify_emails == "all":
                notify_emails = "all"
            else:
                if notify_emails == "none":
                    notify_emails = set()
                if notify_emails != "all":
                    notify_emails.update(request.recipients())

        if isinstance(notify_emails, set):
            notify_emails = ", ".join(notify_emails)
        response.notify_emails = notify_emails

        context = {
            "hint_response": response,
        }
        request_text = ("\n\n".join(request.text_content for request in requests),)
        if request_text:
            context["hint_request"] = {
                "text_content": "\n\n".join(
                    request.text_content for request in requests
                ),
            }

        recipients = response.recipients()

        if not recipients:
            response_email = None
        else:
            plain = render_to_string("hint_answered_email.txt", context)
            html = render_to_string("hint_answered_email.html", context)

            if reply_to_email:
                response_email = Email.ReplyEmail(
                    reply_to_email,
                    plain=plain,
                    html=html,
                    from_address=self.CONTACT_EMAIL_ADDRESS
                    if contact_hq
                    else self.HINT_EMAIL_ADDRESS,
                    to_addresses=recipients,
                    team=self.team,
                )
            else:
                response_email_message = email.message.EmailMessage()
                response_email_message[
                    "Subject"
                ] = f"{settings.EMAIL_SUBJECT_PREFIX}Hint answered for {self.puzzle.name}"
                response_email_message["From"] = self.EMAIL_ADDRESS
                response_email_message["To"] = recipients
                response_email_message.set_content(plain)
                response_email_message.add_alternative(html, subtype="html")
                response_email = Email.FromEmailMessage(
                    response_email_message,
                    status=Email.SENDING,
                    team=self.team,
                )
            if response_email.recipients():
                response.email = response_email
            else:
                response_email = None

        return {
            "response": response,
            "requests": requests,
            "response_email": response_email,
        }

    def __str__(self):
        def abbr(s):
            if len(s) > 50:
                return s[:50] + "..."
            return s

        o = '{}, {}: "{}"'.format(
            self.team.name,
            self.puzzle.name,
            abbr(self.text_content),
        )
        if self.status != self.NO_RESPONSE:
            o = o + " {}".format(self.status)
        return o

    def recipients(self):
        if self.notify_emails == "all":
            return self.team.all_emails
        if self.notify_emails == "none":
            return []
        return [s.strip() for s in self.notify_emails.split(",")]

    @property
    def original_request_id(self):
        "Like root_ancestor_request_id but also for root request"
        return (
            self.pk
            if self.root_ancestor_request_id is None
            else self.root_ancestor_request_id
        )

    @property
    def original_request(self):
        return (
            self
            if self.root_ancestor_request_id is None
            else self.root_ancestor_request
        )

    def original_request_filter(self):
        "Filter to filter by original request"
        original_request_id = self.original_request_id
        return Q(pk=original_request_id) | Q(
            root_ancestor_request_id=original_request_id
        )

    @property
    def task(self):
        return self.tasks.first()

    @property
    def handler(self):
        if task := self.task:
            return task.handler

        # Check the requested hint's handler
        requests = self.request_set.all()
        if not self.is_request and requests:
            request = requests[0]
            return request.handler

        return None

    @property
    def requires_response(self):
        return all(
            (self.is_request, self.response_id is None, self.status == Hint.NO_RESPONSE)
        )

    @classmethod
    def all_requiring_response(cls, queryset=None):
        if queryset is None:
            queryset = cls.objects
        return queryset.filter(
            is_request=True, response_id=None, status=Hint.NO_RESPONSE
        )

    @classmethod
    def clean_up_tasks(cls, hints):
        for hint_request_to_update in hints:
            request_task = hint_request_to_update.task
            if request_task:
                request_task.status = TaskStatus.DONE
                request_task.snooze_time = None
                request_task.snooze_until = None
                request_task.save()

    @property
    def puzzle_hint_url(self):
        "url for teams to view their hints for this puzzle."
        return self.puzzle.puzzle.hints_url

    @property
    def long_status(self):
        return self.STATUSES.get(self.status)

    # these methods are somewhat hunt / discord specific
    def created_discord_message(self):
        solution_url = generate_url("hunt", f"/solutions/{self.puzzle.slug}")
        hints_for_this_puzzle = generate_url(
            "hunt",
            "/spoilr/hints/",
            {"puzzle": self.puzzle.slug},
        )

        stem = "/spoilr/hints/"
        hint_answer_url = generate_url("hunt", stem, {"hint": self.pk})

        return (
            f"Hint #{self.pk} requested on {self.puzzle.puzzle.emoji} {self.puzzle} by {self.team}\n"
            f"**Question:** ```{self.text_content[:1500]}```\n"
            f"**Puzzle:** {solution_url} ({hints_for_this_puzzle})\n"
            f"**Claim and answer hint:** {hint_answer_url}\n"
        )

    def claimed_discord_message(self, claimer):
        return f"Hint #{self.pk} claimed by {claimer}"

    def unclaimed_discord_message(self):
        return f"Hint #{self.pk} was unclaimed"

    @classmethod
    def responded_discord_message(cls, hint_request, hint_response):
        status_name = cls.STATUSES[hint_request.status]
        return (
            f"Hint #{hint_request.pk} resolved by {hint_request.handler}\n"
            f"Hint was requested on {hint_request.puzzle.puzzle.emoji} {hint_request.puzzle} by {hint_request.team}\n"
            f"**Question:** ```{hint_request.text_content[:1500]}```\n"
            f"**Response:** {hint_response.text_content}\n"
            f"**Marked as:** {status_name}\n"
        )


class CannedHint(models.Model):
    """
    Canned hints used as suggestions for responses.
    These should be kept in sync with the PuzzUp version.
    """

    class Meta:
        unique_together = ("puzzle", "description")
        ordering = ["order"]

    puzzle = models.ForeignKey(
        Puzzle, on_delete=models.CASCADE, related_name="canned_hints"
    )
    order = models.FloatField(
        blank=False,
        null=False,
        help_text="Order in the puzzle - use 0 for a hint at the very beginning of the puzzle, or 100 for a hint on extraction, and then do your best to extrapolate in between. Decimals are okay. For multiple subpuzzles, assign a whole number to each subpuzzle and use decimals off of that whole number for multiple hints in the subpuzzle.",
    )
    description = models.CharField(
        max_length=1000,
        blank=False,
        null=False,
        help_text="A description of when this hint should apply",
    )
    keywords = models.CharField(
        max_length=100,
        blank=True,
        null=False,
        help_text="Comma-separated keywords to look for in hunters' hint requests before displaying this hint suggestion",
    )
    content = models.CharField(
        max_length=1000,
        blank=False,
        null=False,
        help_text="Canned hint to give a team (can be edited by us before giving it)",
    )

    def get_keywords(self):
        return self.keywords.split(",")

    def __str__(self):
        return f"Hint #{self.order} for {self.puzzle}"
