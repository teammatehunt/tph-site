import contextlib
import datetime
import email
import email.message
import email.policy
import itertools
import logging
import math
import smtplib
import time
import traceback
from collections import namedtuple

from django.conf import settings
from django.db import transaction
from django.template import Context as TemplateContext
from django.template import Template

if settings.IS_PYODIDE:
    get_task_logger = logging.getLogger
else:
    from celery.utils.log import get_task_logger
    import imapclient

from spoilr.core.models import User, UserTeamRole
from spoilr.email.models import BadEmailAddress, Email, EmailTemplate
from spoilr.hints.models import Hint
from spoilr.registration.models import TeamRegistrationInfo

from puzzles.celery import celery_app
from puzzles.models import Team
from puzzles.utils import redis_lock

task_logger = get_task_logger(__name__)  # for Celery tasks
django_logger = logging.getLogger("django")  # for single process tasks


# port 465 starts in SSL mode, port 587 needs to upgrade the connection
SMTP = smtplib.SMTP if settings.EMAIL_PORT == 587 else smtplib.SMTP_SSL


class ImapClient:
    class ConnectionError(RuntimeError):
        pass

    def __init__(
        self,
        host,
        account,
        password,
        timestamp=None,
        timestamp_buffer=60,
        folder="INBOX",
        timeout=None,
        uidvalidity=None,
        modseq=None,
    ):
        self.timestamp = timestamp
        self.timeout = timeout
        self.timestamp_buffer = timestamp_buffer

        self.host = host
        self.account = account
        self.password = password

        self.server = None
        self.uidvalidity = uidvalidity
        self.modseq = modseq
        self.folder = folder

    def connect(self):
        "Connect to the mail server, login, and set connection settings."
        self.close()
        try:
            self.server = imapclient.IMAPClient(self.host)
            self.server.normalise_times = False
            self.server.login(self.account, self.password)
            uidvalidity = self.server.folder_status(self.folder, ("UIDVALIDITY",))[
                b"UIDVALIDITY"
            ]
            if self.uidvalidity is None or uidvalidity != self.uidvalidity:
                self.modseq = None
            self.uidvalidity = uidvalidity
            self.server.select_folder(self.folder, readonly=True)
        except:
            self.close()
            raise

    def close(self):
        if self.server is not None:
            try:
                self.server.logout()
            except:
                pass
        self.server = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def fetch(self):
        "Fetch new emails and process them."
        ts = datetime.datetime.now(datetime.timezone.utc)
        modifiers = []
        fetch_uids = "1:*"  # ALL
        if self.modseq is not None:
            modifiers.append(f"CHANGEDSINCE {self.modseq}")
        elif self.timestamp is not None:
            delta = ts - self.timestamp
            search_window = str(
                math.ceil(delta.total_seconds() + self.timestamp_buffer)
            )
            fetch_uids = self.server.search(["YOUNGER", search_window])
        for uid, data in self.server.fetch(
            fetch_uids, ("RFC822", "INTERNALDATE", "MODSEQ"), modifiers
        ).items():
            raw_content = data[b"RFC822"]
            date = data[b"INTERNALDATE"]
            modseq = max(data[b"MODSEQ"])
            self.process(uid, date, modseq, raw_content)
            if modseq is not None:
                self.modseq = (
                    modseq if self.modseq is None else max(self.modseq, modseq)
                )
        self.timestamp = ts

    def run(self):
        "Continually wait for new emails and process them."
        last_error_timestamp = None
        while True:
            try:
                self.connect()
                if last_error_timestamp is not None:
                    django_logger.info("IMAPClient reconnected!")
                last_error_timestamp = None
                while True:
                    self.fetch()
                    self.server.idle()
                    try:
                        responses = self.server.idle_check(timeout=self.timeout)
                    finally:
                        self.server.idle_done()
            except imapclient.exceptions.LoginError:
                # exit on login error rather than keep retrying so that we
                # don't exceed login limits
                raise
            except Exception as e:
                now = time.time()
                if last_error_timestamp is None or now - last_error_timestamp >= 300:
                    django_logger.error(traceback.format_exc())
                    last_error_timestamp = now
            finally:
                self.close()
            time.sleep(1)

    def process(self, uid, date, modseq, raw_content):
        "Parse a fetched email and add it to the database."
        email_message = email.message_from_bytes(
            raw_content, policy=email.policy.default
        )
        if Email.check_is_from_admin(email_message):
            # Skip admin error reports
            return

        message_id = Email.parseaddr(email_message.get("Message-ID"))
        selectors = {
            "uidvalidity": self.uidvalidity,
            "uid": uid,
        }
        is_authenticated = Email.check_authentication(email_message)
        is_from_us = Email.check_is_from_us(
            email_message, preauthentication=is_authenticated
        )
        if message_id is not None and is_from_us:
            # if this email is already in the database, just update its status
            count = Email.objects.filter(message_id=message_id, is_from_us=True).update(
                **selectors,
                raw_content=raw_content,
                modseq=modseq,
                received_datetime=date,
                status=Email.SENT,
            )
            if count:
                return

        fields = Email.parse_fields_from_message(
            raw_content=raw_content,
            email_message=email_message,
        )
        fields["received_datetime"] = date
        fields["modseq"] = modseq

        from_addresses = email_message.get("From")
        from_addresses = [] if from_addresses is None else from_addresses.addresses
        to_addresses = email_message.get("To")
        to_addresses = [] if to_addresses is None else to_addresses.addresses
        cc_addresses = email_message.get("Cc")
        cc_addresses = [] if cc_addresses is None else cc_addresses.addresses

        # aggregate emails that are not us so that we can attach them to the
        # hint if necessary
        them_addresses = set()
        for address in (*from_addresses, *to_addresses, *cc_addresses):
            addr_spec = Email.parseaddr(address)
            if addr_spec and not Email.check_is_address_us(address):
                them_addresses.add(addr_spec)

        # determine whether this email is part of a hint thread
        root_reference_id = fields.get("root_reference_id")
        ancestor_hint = None
        if root_reference_id is not None:
            root_email = (
                Email.objects.filter(message_id=root_reference_id)
                .select_related("hint")
                .only("hint")
                .first()
            )
            try:
                ancestor_hint = root_email and root_email.hint
            except Email.hint.RelatedObjectDoesNotExist:
                ancestor_hint = None

        # check if this email part of a bounce / unsubscribe / resubscribe action
        bounced_address = Email.get_bounced_address(email_message)
        unsubscribed_address = Email.get_unsubscribed_address(
            email_message, preauthentication=is_authenticated
        )
        resubscribed_address = Email.get_resubscribed_address(
            email_message, preauthentication=is_authenticated
        )

        # set status
        answered_a_thread = False
        if bounced_address:
            fields["status"] = Email.RECEIVED_BOUNCE
        elif is_from_us:
            fields["status"] = Email.SENT
            if email_message.get("References"):
                answered_a_thread = True
        elif ancestor_hint:
            fields["status"] = Email.RECEIVED_HINT
        elif unsubscribed_address:
            fields["status"] = Email.RECEIVED_UNSUBSCRIBE
        elif resubscribed_address:
            fields["status"] = Email.RECEIVED_RESUBSCRIBE
        else:
            fields["status"] = Email.RECEIVED_NO_REPLY
        need_to_save_multiple_objects = any(
            (
                answered_a_thread,
                ancestor_hint,
                bounced_address,
                unsubscribed_address,
                resubscribed_address,
            )
        )

        fields["is_authenticated"] = is_authenticated
        fields["is_from_us"] = is_from_us
        fields["is_spam"] = Email.check_is_spam(email_message)
        fields["created_via_webapp"] = False
        from_address = Email.parseaddr(email_message.get("From"))
        if from_address and not is_from_us:
            registration = TeamRegistrationInfo.objects.filter(
                contact_email=from_address
            ).first()
            if registration and registration.team_id:
                fields["team_id"] = registration.team_id

        cm = (
            transaction.atomic()
            if need_to_save_multiple_objects
            else contextlib.nullcontext()
        )
        with cm:
            email_obj, email_was_created = Email.objects.get_or_create(
                **selectors, defaults=fields
            )
            if answered_a_thread:
                Email.objects.filter(
                    message_id__in=email_obj.reference_ids,
                    status=Email.RECEIVED_NO_REPLY,
                ).update(
                    response=email_obj,
                    status=Email.RECEIVED_ANSWERED,
                )

            if bounced_address:
                BadEmailAddress.objects.get_or_create(
                    email=bounced_address,
                    reason=BadEmailAddress.BOUNCED,
                )
            elif unsubscribed_address:
                BadEmailAddress.objects.get_or_create(
                    email=unsubscribed_address,
                    defaults={
                        "reason": BadEmailAddress.UNSUBSCRIBED,
                    },
                )
            elif resubscribed_address:
                BadEmailAddress.objects.filter(
                    email=resubscribed_address,
                ).delete()
            if ancestor_hint:
                Hint.objects.get_or_create(
                    email=email_obj,
                    defaults={
                        "team": ancestor_hint.team,
                        "puzzle": ancestor_hint.puzzle,
                        "root_ancestor_request_id": ancestor_hint.original_request_id,
                        "is_request": not is_from_us,
                        "text_content": email_obj.text_content,
                        "notify_emails": ", ".join(them_addresses)
                        if them_addresses
                        else "none",
                    },
                )

    @classmethod
    def create_and_run(cls):
        "Start client with defined settings."
        last_email = (
            Email.objects.exclude(status__in=(Email.SENDING, Email.DRAFT))
            .order_by("received_datetime")
            .only(
                "received_datetime",
                "uidvalidity",
                "modseq",
            )
            .last()
        )
        timestamp = None
        uidvalidity = None
        modseq = None
        if last_email is not None:
            timestamp = last_email.received_datetime
            uidvalidity = last_email.uidvalidity
            modseq = last_email.modseq
        with cls(
            host=settings.EMAIL_HOST,
            account=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            timestamp=timestamp,
            uidvalidity=uidvalidity,
            modseq=modseq,
        ) as client:
            client.run()


@celery_app.task
def task_send_email(
    pk,
    *,
    message_id=None,
    now=False,
    cooldown=Email.RESEND_COOLDOWN,  # minimum seconds between retries
    blocking_timeout=5,  # max time to wait for lock
    active_connection=None,
):
    """
    Attempt to send an email with a given pk.

    This is idempotent and includes logic to make sure that we don't double
    send. There are a number of checks to make sure we don't do bad things or
    try to send things that are likely to get us classified as spam. Failures
    cause the email to not be sent, but this function can be called again.
    """
    with redis_lock(
        f"task_send_email:{pk}", timeout=cooldown, blocking_timeout=blocking_timeout
    ):
        assert settings.EMAIL_PORT in (465, 587)
        email_obj = Email.objects.get(pk=pk)
        if email_obj.status == Email.CANCELLED:
            return

        assert email_obj.status == Email.SENDING
        if message_id is not None:
            assert message_id == email_obj.message_id
        timestamp_now = datetime.datetime.now(datetime.timezone.utc)
        if not now:
            assert email_obj.scheduled_datetime <= timestamp_now
        if email_obj.attempted_send_datetime is not None:
            satisfies_cooldown = (
                email_obj.attempted_send_datetime + datetime.timedelta(seconds=cooldown)
                <= timestamp_now
            )
            assert satisfies_cooldown
        assert email_obj.raw_content
        email_message = email.message_from_bytes(
            email_obj.raw_content, policy=email.policy.default
        )
        assert not email_message.defects
        assert (
            email_obj.from_address
            and email_obj.from_address
            == email.utils.parseaddr(email_obj.from_address)[1]
        )
        assert (
            Email.Address(addr_spec=email_obj.from_address).domain
            == settings.EMAIL_USER_DOMAIN
        )
        if settings.EMAIL_SENDFROM_BOUNCES_ADDRESS:
            # Put the bounces address on the envelope so that we can detect and
            # process email addresses that bounce.
            sendfrom_address = (
                f"{settings.EMAIL_BOUNCES_LOCALNAME}@{settings.EMAIL_USER_DOMAIN}"
            )
        else:
            sendfrom_address = email_obj.from_address
        recipients = []
        all_recipients = []
        invalid_recipients = []
        for recipient in email_obj.all_recipients:
            all_recipients.append(recipient)
            if not (recipient and recipient == email.utils.parseaddr(recipient)[1]):
                invalid_recipients.append(recipient)
                continue
            if not settings.IS_TEST or recipient in settings.DEV_EMAIL_WHITELIST:
                recipients.append(recipient)
        if invalid_recipients:
            task_logger.warn(
                f"Got ill-formatted recipients {invalid_recipients} for email with Subject: {email_message.get('Subject', '')} Message-Id: {email_message.get('Message-ID')}. Ignoring."
            )
        if len(recipients) != len(all_recipients):
            task_logger.info(
                f"Would have sent email with Subject: {email_message.get('Subject', '')} Message-Id: {email_message.get('Message-ID')} to {all_recipients}. Instead sending to {recipients}."
            )
        email_obj.attempted_send_datetime = timestamp_now
        email_obj.save(update_fields=("attempted_send_datetime",))
        if recipients:
            task_logger.info(
                f"Sending email with Subject: {email_message.get('Subject', '')!r} Message-Id: {email_message.get('Message-ID')} to {recipients}."
            )
            if active_connection is not None:
                connection = active_connection
                cm = contextlib.nullcontext()
            else:
                connection = SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
                cm = connection
            with cm:
                if connection is not active_connection:
                    if settings.EMAIL_PORT == 587:
                        connection.starttls()
                    connection.login(
                        settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD
                    )
                connection.sendmail(
                    sendfrom_address,
                    recipients,
                    email_obj.raw_content,
                )
                task_logger.info(f"Sent email to {recipients}: {email_obj.subject}")
        elif settings.IS_TEST:
            task_logger.info(f"Would have sent email:\n{email_obj.raw_content}\n")


# This is not hooked up to anything
@celery_app.task
def task_resend_emails(
    *,
    pks=None,
    parallel=False,
    blocking_timeout=0,  # don't wait by default
):
    """
    Attempt to resend unsent emails.

    pks: filter to only send if pk in pks
    parallel: send simultaneously in different threads. Note that this causes
        each email to be sent on a new SMTP connection.
    """
    filter_kwargs = {
        "status": Email.SENDING,
        "scheduled_datetime__lt": datetime.datetime.now(datetime.timezone.utc),
    }
    if pks is not None:
        filter_kwargs["pk__in"] = pks
    pks = Email.objects.filter(**filter_kwargs).values_list("pk", flat=True)
    if parallel:
        for pk in pks:
            task_send_email.delay(pk, blocking_timeout=blocking_timeout)
    elif pks:
        with SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as connection:
            if settings.EMAIL_PORT == 587:
                connection.starttls()
            connection.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            for pk in pks:
                try:
                    task_send_email(
                        pk,
                        blocking_timeout=blocking_timeout,
                        active_connection=connection,
                    )
                except:
                    task_logger.error(traceback.format_exc())


Batch = namedtuple("Batch", ("user", "team", "address_index", "addresses"))


def _get_email_template_batches(template_obj):
    batches = []

    if template_obj.recipients == EmailTemplate.RECIPIENT_TEAMS:
        teams = Team.objects.filter(
            pk__gt=template_obj.last_team_pk,
        ).order_by("pk")
        for team in teams:
            addresses = team.all_emails
            if addresses:
                batches.append(
                    Batch(
                        user=None,
                        team=team,
                        address_index=None,
                        addresses=addresses,
                    )
                )

    else:
        assert template_obj.recipients == EmailTemplate.RECIPIENT_BATCH_ADDRESSES
        addresses = [
            (idx, address)
            for idx, address in enumerate(template_obj.addresses)
            if idx > template_obj.last_address_index
        ]
        batch_size = template_obj.batch_size
        for batch_iter in itertools.zip_longest(*(iter(addresses),) * batch_size):
            batch = list(filter(None, batch_iter))
            batches.append(
                Batch(
                    user=None,
                    team=None,
                    address_index=max([idx for idx, _ in batch]),
                    addresses=[address for _, address in batch],
                )
            )

    return batches


@celery_app.task
def task_send_email_template(
    pk,
    *,
    blocking_timeout=5,  # max time to wait for lock
):
    """
    Idempotentally attempt to send emails from a template (to all users, etc).
    """
    with redis_lock(
        f"task_send_email_template:{pk}", blocking_timeout=blocking_timeout
    ):
        assert settings.EMAIL_PORT in (465, 587)
        template_obj = EmailTemplate.objects.get(pk=pk)
        assert template_obj.status in (EmailTemplate.SCHEDULED, EmailTemplate.SENDING)
        timestamp_now = datetime.datetime.now(datetime.timezone.utc)
        assert template_obj.scheduled_datetime <= timestamp_now
        assert Email.check_is_address_us(
            template_obj.from_address, allow_external=False
        )

        batches = _get_email_template_batches(template_obj)
        if not batches:
            return

        SMTP = smtplib.SMTP if settings.EMAIL_PORT == 587 else smtplib.SMTP_SSL
        with SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as connection:
            if settings.EMAIL_PORT == 587:
                connection.starttls()
            connection.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)

            if template_obj.status == EmailTemplate.SCHEDULED:
                template_obj.status = EmailTemplate.SENDING

            is_first = True
            for batch in batches:
                if not is_first:
                    time.sleep(template_obj.batch_delay_ms / 1000)
                is_first = False

                email_obj = email_obj_for_batch(template_obj, batch)
                if batch.user is not None:
                    template_obj.last_user_pk = max(
                        template_obj.last_user_pk, batch.user.pk
                    )
                if batch.team is not None:
                    template_obj.last_team_pk = max(
                        template_obj.last_team_pk, batch.team.pk
                    )
                if batch.address_index is not None:
                    template_obj.last_address_index = max(
                        template_obj.last_address_index, batch.address_index
                    )
                with transaction.atomic():
                    template_obj.save(
                        update_fields=(
                            "status",
                            "last_user_pk",
                            "last_team_pk",
                            "last_address_index",
                        )
                    )
                    if email_obj.all_recipients:
                        email_obj.save()
                        transaction.on_commit(
                            lambda: task_send_email(
                                email_obj.pk,
                                active_connection=connection,
                            )
                        )
        template_obj.status = EmailTemplate.SENT
        template_obj.save(update_fields=("status",))


def email_obj_for_batch(email_template, batch, message_id=None):
    email_message = email.message.EmailMessage()
    email_message["From"] = email_template.from_address
    email_message["Subject"] = email_template.subject
    if message_id is None:
        message_id = Email.make_message_id()
    email_message["Message-ID"] = message_id

    context = {
        "because_registered": email_template.recipients
        != EmailTemplate.RECIPIENT_BATCH_ADDRESSES,
    }
    if batch.team is not None:
        context["team"] = batch.team
    elif (
        batch.user is not None
        and len(batch.addresses) == 1
        and batch.user.email == batch.addresses[0]
    ):
        context["user"] = batch.user
        context["name"] = batch.user.name or batch.user.email
        context["email"] = batch.user.email
        context["team"] = batch.user.team

    text_content, html_content = render_email_template(
        email_template.text_content,
        email_template.html_content,
        message_id,
        **context,
    )
    email_message.set_content(text_content)
    email_message.add_alternative(html_content, subtype="html")

    kwargs = {}
    if email_template.recipients in (EmailTemplate.RECIPIENT_TEAMS,):
        email_message["To"] = batch.addresses
    else:
        assert email_template.recipients in (EmailTemplate.RECIPIENT_BATCH_ADDRESSES,)
        kwargs["bcc_addresses"] = batch.addresses

    email_obj = Email.FromEmailMessage(
        email_message,
        **kwargs,
        template=email_template,
        status=Email.SENDING,
        include_unsubscribe_header=True,
    )
    return email_obj


def render_email_template(text_content, html_content, message_id, **kwargs):
    text_template = Template(
        '{% extends "email_template_template.txt" %}\n'
        "{% block content %}"
        f"{text_content}"
        "{% endblock %}"
    )
    html_template = Template(
        '{% extends "email_template_template.html" %}\n'
        "{% block content %}"
        f"{html_content}"
        "{% endblock %}"
    )
    unsubscribe_url = Email.get_unsubscribe_link(message_id)
    kwargs["unsubscribe_url"] = unsubscribe_url
    kwargs.setdefault("because_registered", False)
    context = TemplateContext(kwargs)
    text = text_template.render(context)
    html = html_template.render(context)
    return text, html


@celery_app.task
def task_create_testing_email():
    email_message = email.message.EmailMessage()
    email_message["From"] = f"hello@{settings.EMAIL_USER_DOMAIN}"
    email_message["To"] = f"testing@{settings.EMAIL_USER_DOMAIN}"
    email_message["Subject"] = "Sending a test email"
    email_message.set_content("Lorem ipsum!")
    email_obj = Email.FromEmailMessage(
        email_message,
        status=Email.SENDING,
        is_from_us=True,
        created_via_webapp=True,
    )
    email_obj.save()
