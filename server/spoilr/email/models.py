import distutils.util
import email
import email.headerregistry
import email.policy
import email.utils
import html
import re

import dateutil.parser
import html2text
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Q
from django.utils import timezone
from pyexpat import model
from spoilr.core.models import Interaction, Team
from spoilr.hq.models import Handler, Task
from spoilr.utils import generate_url


class EmailTemplate(models.Model):
    """Template for a mass email."""

    SCHEDULED = "SCHD"
    SENDING = "SOUT"
    SENT = "SENT"
    DRAFT = "DRFT"
    CANCELLED = "CANC"

    STATUSES = {
        SCHEDULED: "Scheduled",
        SENDING: "Sending",
        SENT: "Sent",
        DRAFT: "Draft",
        CANCELLED: "Cancelled",
    }

    RECIPIENT_TEAMS = "TE"
    RECIPIENT_BATCH_ADDRESSES = "AD"
    RECIPIENT_OPTIONS = {
        RECIPIENT_TEAMS: "all_teams",  # send to teams individually (teammmembers to)
        RECIPIENT_BATCH_ADDRESSES: "batch_addresses",  # send to batches of addresses (bcc)
    }

    subject = models.TextField(blank=True)
    text_content = models.TextField(blank=True)
    html_content = models.TextField(blank=True)
    from_address = models.TextField()
    scheduled_datetime = models.DateTimeField()
    status = models.CharField(
        choices=tuple(STATUSES.items()), max_length=4, default=DRAFT
    )
    # Describes how to send emails
    recipients = models.CharField(
        choices=tuple(RECIPIENT_OPTIONS.items()), max_length=2
    )
    # Only used if in RECIPIENT_BATCH_ADDRESSES mode
    addresses = models.JSONField(blank=True, default=list)
    batch_size = models.IntegerField(default=50)  # for batch_users
    # Delay in ms between batches. Does not include the time to make the SMTP
    # request for each batch.
    batch_delay_ms = models.IntegerField(default=100)
    # for internal idempotency checks
    last_user_pk = models.IntegerField(default=-1)
    last_team_pk = models.IntegerField(default=-1)
    last_address_index = models.IntegerField(default=-1)


class BadEmailAddress(models.Model):
    "Email addresses we should not be emailing."
    UNSUBSCRIBED = "UNS"
    BOUNCED = "BOU"

    REASONS = {
        UNSUBSCRIBED: "Unsubscribed",
        BOUNCED: "Bounced",
    }

    email = models.EmailField(primary_key=True)
    reason = models.CharField(choices=tuple(REASONS.items()), max_length=3)


class CannedEmail(models.Model):
    """
    Model for reusable drafts that we will send throughout hunt.

    This is distinct from EmailTemplate, which includes recipients and send status;
    a CannedEmail only contains a subject and body text/html.
    """

    slug = models.SlugField(max_length=200, unique=True)
    subject = models.TextField(
        help_text="Automatically prepended with [Mystery Hunt]", null=False, blank=False
    )
    from_address = models.CharField(
        max_length=256, help_text="The email address this email should be sent from"
    )
    text_content = models.TextField(blank=True)
    html_content = models.TextField(blank=True)
    interaction = models.ForeignKey(
        Interaction,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="If this field is blank, it will show up for all interactions.",
    )
    description = models.CharField(
        max_length=1000,
        blank=False,
        null=False,
        help_text="A description of when this email should be used, including to which recipients",
    )

    def __str__(self):
        return f"{self.slug}: {self.subject}"


class EmailManager(models.Manager):
    def get_queryset(self, *args, **kwargs):
        # Prefetches the round and event status automatically.
        return super().get_queryset(*args, **kwargs).prefetch_related("tasks")


class Email(models.Model):
    """Model for each individual email sent or received."""

    objects = EmailManager()

    # Constants
    SENDING = "SOUT"  # if sending via SMTP server but haven't read it back with IMAP
    SENT = "SENT"
    RECEIVED_NO_REPLY = "RNR"
    RECEIVED_ANSWERED = "RANS"
    RECEIVED_NO_REPLY_REQUIRED = "RNRR"
    RECEIVED_HINT = "RH"
    RECEIVED_BOUNCE = "RB"
    RECEIVED_UNSUBSCRIBE = "RUNS"
    RECEIVED_RESUBSCRIBE = "RSUB"
    DRAFT = "DRFT"  # TODO: is this useful?
    CANCELLED = "CANC"  # only used for outgoing scheduled emails

    STATUSES = {
        SENDING: "Sending",
        SENT: "Sent",
        RECEIVED_NO_REPLY: "Received - No reply",
        RECEIVED_ANSWERED: "Received - Answered",
        RECEIVED_NO_REPLY_REQUIRED: "Received - No reply required",
        RECEIVED_HINT: "Received - Hint",
        RECEIVED_BOUNCE: "Received - Bounce",
        RECEIVED_UNSUBSCRIBE: "Received - Unsubscribe",
        RECEIVED_RESUBSCRIBE: "Received - Resubscribe",
        DRAFT: "Draft",
        CANCELLED: "Cancelled",
    }

    HIDDEN_STATUSES = (
        RECEIVED_NO_REPLY_REQUIRED,
        RECEIVED_BOUNCE,
        RECEIVED_HINT,  # Hint emails show up in hint dashboard
    )

    DEFERRED = object()  # sentinel to detect comparisons against deferred fields
    HEADER_BODY_SEPARATOR_REGEX = re.compile(rb"\r?\n\r?\n|\r\n?\r\n?")
    RESEND_COOLDOWN = 30  # seconds

    raw_content = models.BinaryField(blank=True)
    # derived from email raw_content
    subject = models.TextField(blank=True)
    text_content = models.TextField(blank=True)
    html_content = models.TextField(blank=True)
    header_content = models.BinaryField(blank=True)
    from_address = models.TextField(blank=True)
    # to, cc, bcc addresses are lists
    to_addresses = models.JSONField(blank=True, default=list)
    cc_addresses = models.JSONField(blank=True, default=list)
    # This will be blank on emails we receive.
    bcc_addresses = models.JSONField(blank=True, default=list)
    has_attachments = models.BooleanField(default=False)
    message_id = models.TextField(db_index=True, blank=True)
    in_reply_to_id = models.TextField(
        db_index=True, blank=True
    )  # previous email in chain
    root_reference_id = models.TextField(
        db_index=True, blank=True
    )  # initial email in chain
    reference_ids = models.JSONField(blank=True, default=list)  # all emails in chain
    # Date header
    sent_datetime = models.DateTimeField(null=True, blank=True)
    # Spam detection
    is_spam = models.BooleanField(default=False)
    is_authenticated = models.BooleanField(default=False)  # check for DMARC

    # other email info
    attempted_send_datetime = models.DateTimeField(
        null=True, blank=True
    )  # used internally
    received_datetime = models.DateTimeField(
        default=timezone.now,
    )  # will be updated with timestamp from SMTP server

    # These fields are set by IMAP
    uidvalidity = models.IntegerField(null=True, blank=True)  # set by IMAP
    uid = models.IntegerField(null=True, blank=True)  # set by IMAP
    modseq = models.IntegerField(null=True, blank=True)  # set by IMAP

    is_from_us = models.BooleanField()
    created_via_webapp = models.BooleanField()  # otherwise was found by IMAP
    scheduled_datetime = models.DateTimeField(
        default=timezone.now,
    )  # for emails we are sending
    template = models.ForeignKey(
        EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True
    )
    canned_template = models.ForeignKey(
        CannedEmail, on_delete=models.SET_NULL, null=True, blank=True
    )
    opened = models.BooleanField(default=False)  # if we want to set tracking pixels

    status = models.CharField(choices=tuple(STATUSES.items()), max_length=4)
    # we can set the team if it is known but in general emails won't have a team
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, default=None
    )
    interaction = models.ForeignKey(
        Interaction, blank=True, null=True, on_delete=models.SET_NULL
    )

    tasks = GenericRelation(Task, related_query_name="task")
    # Used for replies
    author = models.ForeignKey(
        Handler, on_delete=models.SET_NULL, null=True, blank=True
    )

    response = models.ForeignKey(
        "self",
        related_name="request_set",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    @property
    def task(self):
        tasks = list(self.tasks.all())
        task = tasks[0] if tasks else None
        return task

    @property
    def handler(self):
        task = self.task
        if task is None:
            author = self.author
            if author == "":
                return None
            return author
        return task.handler

    def __init__(self, *args, **kwargs):
        """
        Prefer to instantiate via FromRawContent, FromEmailMessage, or
        ReplyEmail, plus non-RFC822 email attributes (such as bcc and all our
        custom metadata).

        This saves the initial values of some attributes so that we can check
        if it changed during save().
        """
        super().__init__(*args, **kwargs)
        # check against __dict__ to test for deferred fields
        for field in ("raw_content", "header_content"):
            if field in self.__dict__:
                if isinstance(getattr(self, field), memoryview):
                    setattr(self, field, getattr(self, field).tobytes())
        # NB: currently will cause a db query for instantiating this instance
        self._original_handler = self.handler

    def save(self, *args, **kwargs):
        # This is not handled in all cases - IE get_or_create - more for development TODO address
        # assert self._original_handler is not self.DEFERRED or not self._state.adding
        super().save(*args, **kwargs)

    @classmethod
    def FromRawContent(cls, raw_content, **kwargs):
        email_kwargs = cls.parse_fields_from_message(
            raw_content=raw_content,
        )
        email_kwargs.update(kwargs)
        return cls(**email_kwargs)

    @classmethod
    def make_message_id(cls):
        return email.utils.make_msgid(domain=settings.EMAIL_USER_DOMAIN)

    @classmethod
    def FromEmailMessage(
        cls,
        email_message,
        add_defaults=True,
        check_addresses=True,
        include_unsubscribe_header=False,
        exclude_bounced_only=False,
        **kwargs,
    ):
        """
        If add_defaults is set, will add default fields like Message-ID.
        """
        email_kwargs = {}
        is_from_us = cls.check_is_from_us(email_message, check_authentication=False)
        if add_defaults:
            if not email_message.get("Message-ID"):
                email_message["Message-ID"] = cls.make_message_id()
            email_kwargs["is_authenticated"] = is_from_us or cls.check_authentication(
                email_message
            )
            email_kwargs["is_from_us"] = is_from_us
            email_kwargs["is_spam"] = not is_from_us and cls.check_is_spam(
                email_message
            )
            email_kwargs["created_via_webapp"] = True
            if is_from_us and include_unsubscribe_header:
                unsubscribe_mailto = f"{settings.EMAIL_UNSUBSCRIBE_LOCALNAME}@{settings.EMAIL_USER_DOMAIN}"
                unsubscribe_link = cls.get_unsubscribe_link(email_message["Message-ID"])
                email_message[
                    "List-Unsubscribe"
                ] = f"<mailto:{unsubscribe_mailto}>, <{unsubscribe_link}>"
        if check_addresses and is_from_us:
            recipients = []
            email_to = email_message.get("To")
            email_cc = email_message.get("Cc")
            to_addresses = kwargs.get("to_addresses")
            recipients.extend(cls.parseaddrs(email_to) or [])
            recipients.extend(cls.parseaddrs(email_cc) or [])
            recipients.extend(kwargs.get("to_addresses", []))
            recipients.extend(kwargs.get("cc_addresses", []))
            recipients.extend(kwargs.get("bcc_addresses", []))
            if recipients:
                bad_recipients = set(
                    BadEmailAddress.objects.filter(
                        email__in=recipients,
                        **(
                            {"reason": BadEmailAddress.BOUNCED}
                            if exclude_bounced_only
                            else {}
                        ),
                    ).values_list("email", flat=True)
                )
                if email_to is not None:
                    del email_message["To"]
                    email_message["To"] = (
                        address
                        for address in email_to.addresses
                        if cls.parseaddr(address) not in bad_recipients
                    )
                if email_cc is not None:
                    del email_message["Cc"]
                    email_message["Cc"] = (
                        address
                        for address in email_cc.addresses
                        if cls.parseaddr(address) not in bad_recipients
                    )
                for key in ("to_addresses", "cc_addresses", "bcc_addresses"):
                    addresses = kwargs.get(key)
                    if addresses is not None:
                        kwargs[key] = [
                            address
                            for address in addresses
                            if address not in bad_recipients
                        ]
        email_kwargs.update(
            cls.parse_fields_from_message(
                email_message=email_message,
            )
        )
        email_kwargs.update(kwargs)
        return cls(**email_kwargs)

    @classmethod
    def from_canned_email(
        cls,
        canned_email: CannedEmail,
        *,
        from_domain,
        to_addresses,
        bcc_addresses,
        reply_to,
        **kwargs,
    ):
        # Override the domain of the canned email for staging and testing.
        name, addr = email.utils.parseaddr(canned_email.from_address)
        addr = "@".join([addr.split("@")[0], from_domain])
        from_address = email.utils.formataddr((name, addr))

        mail = email.message.EmailMessage()
        mail["Subject"] = canned_email.subject
        mail.set_content(canned_email.text_content)
        mail["From"] = from_address
        mail["To"] = ", ".join(to_addresses)
        mail.add_alternative(canned_email.html_content, subtype="html")
        mail["Reply-To"] = reply_to

        return cls.FromEmailMessage(
            email_message=mail,
            canned_template=canned_email,
            bcc_addresses=bcc_addresses,
            **kwargs,
        )

    @classmethod
    def ReplyEmail(cls, reply_to_obj, plain=None, html=None, reply_all=False, **kwargs):
        "Create a reply response for another email. Sets status to SENDING by default."
        assert plain is not None or html is not None
        if plain is None and html is not None:
            plain = Email.html2text(html)
        if html is None and plain is not None:
            html = Email.text2html(plain)
        reply_to_message = reply_to_obj.parse()
        reply_to_plain = reply_to_message.get_body("plain")
        reply_to_plain = reply_to_plain and reply_to_plain.get_content()
        reply_to_html = reply_to_message.get_body("html")
        reply_to_html = reply_to_html and reply_to_html.get_content()
        if reply_to_plain is None and reply_to_html is not None:
            reply_to_plain = Email.html2text(reply_to_html)
        if reply_to_html is None and reply_to_plain is not None:
            reply_to_html = Email.text2html(reply_to_plain)

        reply_to_from = reply_to_message.get("From")
        reply_to_to = reply_to_message.get("To")
        reply_to_to = [] if reply_to_to is None else reply_to_to.addresses
        reply_to_cc = reply_to_message.get("Cc")
        reply_to_cc = [] if reply_to_cc is None else reply_to_cc.addresses
        us = kwargs.get("from_address")
        reply_all_recipients = []
        for recipient in reply_to_to:
            if us is None and Email.check_is_address_us(recipient):
                us = recipient
            elif recipient != us:
                reply_all_recipients.append(recipient)
        reply_to_reply_to = reply_to_message.get("Reply-To", reply_to_from)
        reply_to_message_id = reply_to_message.get("Message-ID")
        reference_ids = reply_to_message.get("References")
        if reply_to_message_id or reference_ids:
            if reference_ids is None:
                reference_ids = reply_to_message_id
            else:
                reference_ids += f", {reply_to_message_id}"
        subject = reply_to_obj.subject
        if not subject.startswith("Re:"):
            subject = f"Re: {subject}"

        reply_to_date = reply_to_obj.sent_datetime or reply_to_obj.received_datetime
        if reply_to_date is None:
            wrote_str = f"{reply_to_from} wrote:"
        else:
            datestr = reply_to_date.strftime("%a, %b %d, %Y at %I:%M %p").replace(
                " 0", " "
            )
            wrote_str = f"On {datestr}, {reply_to_from} wrote:"

        plain += (
            "\n\n"
            + wrote_str
            + "\n\n"
            + "\n".join(f"> {line}" for line in reply_to_plain.strip().split("\n"))
        )
        html = f'<div>{html}</div><div><br/><div>{wrote_str}<br/></div><blockquote style="border-left: 1px solid rgb(204,204,204); padding-left:1ex">{reply_to_html}</blockquote></div>'

        email_message = email.message.EmailMessage()
        email_message["Subject"] = subject
        # this webapp is not set up to send mail from an external domain (eg. gmail)
        if cls.check_is_address_us(us, allow_external=False):
            email_message["From"] = us
        else:
            email_message["From"] = f"info@{settings.EMAIL_USER_DOMAIN}"
        to_addresses = kwargs.get("to_addresses")
        if to_addresses is not None:
            email_message["To"] = to_addresses
        else:
            email_message["To"] = reply_to_reply_to
            if reply_all and reply_all_recipients:
                email_message["Cc"] = reply_all_recipients
        if reply_to_message_id is not None:
            email_message["In-Reply-To"] = reply_to_message_id
        if reference_ids is not None:
            email_message["References"] = reference_ids
        email_message.set_content(plain)
        email_message.add_alternative(html, subtype="html")

        email_kwargs = {}
        email_kwargs["status"] = Email.SENDING
        if reply_to_obj.team is not None:
            email_kwargs["team"] = reply_to_obj.team
        email_kwargs.update(kwargs)
        # When replying, only exclude bounced, not unsubscribed
        return cls.FromEmailMessage(
            email_message, exclude_bounced_only=True, **email_kwargs
        )

    @classmethod
    def parse_fields_from_message(
        cls, raw_content=None, email_message=None, populate_text_content=True
    ):
        email_kwargs = {
            "raw_content": raw_content,
        }
        if raw_content is not None:
            email_message = email.message_from_bytes(
                raw_content, policy=email.policy.default
            )
        if email_message is not None:
            if raw_content is None:
                raw_content = email_message.as_bytes()
                email_kwargs["raw_content"] = raw_content
            email_kwargs["subject"] = email_message.get("Subject")
            if populate_text_content:
                text_content, html_content = cls.make_text_content(email_message)
                email_kwargs["text_content"] = text_content
                email_kwargs["html_content"] = html_content
            email_kwargs["header_content"] = cls.HEADER_BODY_SEPARATOR_REGEX.split(
                raw_content.strip(), 1
            )[0].strip()
            # has_attachments will be true if the email has images or attached
            # files or other parts that are not understood
            has_attachments = False
            for part in email_message.walk():
                if part.is_attachment():
                    has_attachments = True
                if part.get_content_maintype() not in ("text", "multipart"):
                    has_attachments = True
            email_kwargs["has_attachments"] = has_attachments
            email_kwargs["message_id"] = cls.parseaddr(email_message.get("Message-ID"))
            email_kwargs["in_reply_to_id"] = cls.parseaddr(
                email_message.get("In-Reply-To")
            )
            for reference_ids in email_message.get_all("References", []):
                for reference_id in reference_ids.strip().split():
                    reference_id = cls.parseaddr(reference_id)
                    if reference_id:
                        email_kwargs.setdefault("root_reference_id", reference_id)
                        email_kwargs.setdefault("reference_ids", []).append(
                            reference_id
                        )
            email_kwargs["from_address"] = cls.parseaddr(email_message.get("From"))
            email_kwargs["to_addresses"] = cls.parseaddrs(email_message.get("To"))
            email_kwargs["cc_addresses"] = cls.parseaddrs(email_message.get("Cc"))
            try:
                # fails on ill-formatted date
                date = email_message.get("Date")
            except:
                date = None
            if date is not None:
                email_kwargs["sent_datetime"] = date.datetime
            # no bcc in email headers
            for key, value in list(email_kwargs.items()):
                if value is None:
                    del email_kwargs[key]
        return email_kwargs

    @classmethod
    def parseaddrs(cls, addresses):
        if addresses is None:
            return []
        return list(filter(None, map(cls.parseaddr, addresses.addresses)))

    @classmethod
    def parseaddr(cls, address):
        if isinstance(address, email.headerregistry.AddressHeader):
            addresses = cls.parseaddrs(address)
            return addresses[0] if addresses else None
        if isinstance(address, email.headerregistry.Address):
            return address.addr_spec if address.domain else None
        return None if address is None else email.utils.parseaddr(address)[1]

    def parse(self):
        return email.message_from_bytes(self.raw_content, policy=email.policy.default)

    def headers(self):
        return email.parser.BytesHeaderParser(policy=email.policy.default).parsebytes(
            self.header_content
        )

    def recipients(self, bcc=True):
        recipients = []
        recipients.extend(self.to_addresses)
        recipients.extend(self.cc_addresses)
        if bcc:
            recipients.extend(self.bcc_addresses)
        return recipients

    @property
    def all_recipients(self):
        return self.recipients()

    @property
    def requires_response(self):
        return self.status == Email.RECEIVED_NO_REPLY

    @property
    def long_status(self):
        return self.STATUSES.get(self.status)

    @property
    def is_unsent(self):
        return self.status == Email.SENDING

    @staticmethod
    def Address(*args, **kwargs):
        try:
            return email.headerregistry.Address(*args, **kwargs)
        except email.errors.MessageError:
            return email.headerregistry.Address()

    @classmethod
    def check_authentication(cls, email_message, preauthentication=None):
        """
        Check the authentication results header to verify that the FROM header
        is not being forged.
        """
        if preauthentication is not None:
            return preauthentication
        authentication_results = email_message.get("Authentication-Results")
        if authentication_results is None:
            return False
        authentication_parts = authentication_results.split(";")
        if authentication_parts[0].strip() != settings.EMAIL_HOST:
            return False
        passed = False
        for part in authentication_parts[1:]:
            result = part.strip().split()[0]
            if result in ("auth=pass", "dmarc=pass"):
                passed = True
        if not passed:
            return False
        return True

    @classmethod
    def check_is_from_us(
        cls, email_message, check_authentication=True, preauthentication=None
    ):
        "Check the FROM header and authentication results of an EmailMessage."
        from_address = email_message.get("From")
        if from_address is None:
            return False
        if not cls.check_is_address_us(from_address):
            return False
        if check_authentication and not cls.check_authentication(
            email_message, preauthentication=preauthentication
        ):
            return False
        return True

    @classmethod
    def check_is_address_us(cls, address, allow_external=True):
        address = cls.parseaddr(address)
        if address is None:
            return False
        if settings.IS_TEST:
            # treat dev testing emails as external
            if address in settings.DEV_EMAIL_WHITELIST:
                return False
        domain_match = Email.Address(addr_spec=address).domain in (
            settings.EMAIL_USER_DOMAIN,
            *settings.ALTERNATE_EMAIL_DOMAINS,
        )
        is_external_us = address in settings.EXTERNAL_EMAIL_ADDRESSES
        return domain_match or (allow_external and is_external_us)

    @classmethod
    def check_is_spam(cls, email_message):
        raw_value = email_message.get("X-Spam", "False")
        try:
            value = distutils.util.strtobool(raw_value)
        except ValueError:
            value = False
        return value

    @classmethod
    def check_is_from_admin(cls, email_message):
        from_address = email_message.get("From")
        address = cls.parseaddr(from_address)
        return address == settings.SERVER_EMAIL

    @classmethod
    def get_bounced_address(cls, email_message):
        """
        Determine if the email was sent to our bounce receiver and parse the
        offending address. Returns None if not a bounce.
        """
        for address in cls.parseaddrs(email_message.get("To")):
            addr = cls.Address(addr_spec=address)
            if addr.domain != settings.EMAIL_USER_DOMAIN:
                continue
            parts = addr.username.split("+", 1)
            if len(parts) != 2:
                continue
            localname, alias = parts
            if localname != settings.EMAIL_BOUNCES_LOCALNAME:
                continue
            bounced_address = "@".join(alias.rsplit("=", 1))
            if bounced_address != Email.Address(addr_spec=bounced_address).addr_spec:
                continue
            return bounced_address
        return None

    @classmethod
    def _get_from_if_sent_to(
        cls,
        to_address,
        email_message,
        check_authentication=True,
        preauthentication=None,
    ):
        is_match = False
        for address in cls.parseaddrs(email_message.get("To")):
            if address == to_address:
                is_match = True
        if not is_match:
            return None
        if check_authentication and not cls.check_authentication(
            email_message, preauthentication=preauthentication
        ):
            return None
        from_address = cls.parseaddr(email_message.get("From"))
        return from_address

    @classmethod
    def get_resubscribed_address(
        cls, email_message, check_authentication=True, preauthentication=None
    ):
        """
        Determine if the email was sent to our resubscribe receiver and parse the
        offending address. Returns None if not a resubscribe.
        """
        resubscribe_to = (
            f"{settings.EMAIL_RESUBSCRIBE_LOCALNAME}@{settings.EMAIL_USER_DOMAIN}"
        )
        return cls._get_from_if_sent_to(
            resubscribe_to,
            email_message,
            check_authentication=check_authentication,
            preauthentication=preauthentication,
        )

    @classmethod
    def get_unsubscribed_address(
        cls, email_message, check_authentication=True, preauthentication=None
    ):
        """
        Determine if the email was sent to our unsubscribe receiver and parse the
        offending address. Returns None if not an unsubscribe.
        """
        unsubscribe_to = (
            f"{settings.EMAIL_UNSUBSCRIBE_LOCALNAME}@{settings.EMAIL_USER_DOMAIN}"
        )
        return cls._get_from_if_sent_to(
            unsubscribe_to,
            email_message,
            check_authentication=check_authentication,
            preauthentication=preauthentication,
        )

    def get_emails_in_thread_filter(self):
        """
        Makes an intermidiary query to check which of the reference emails were
        from a template (ie, mass email).
        """
        template_ids = set(
            Email.objects.filter(
                message_id__in=self.reference_ids,
                template_id__isnull=False,
            ).values_list("message_id", flat=True)
        )
        if not template_ids:
            root_reference_id = self.root_reference_id or self.message_id
            return Email.objects.filter(
                Q(message_id=root_reference_id) | Q(root_reference_id=root_reference_id)
            )
        for i, _id in enumerate((*self.reference_ids, self.message_id)):
            if _id not in template_ids:
                return Email.objects.filter(
                    Q(message_id=_id) | Q(**{f"reference_ids__{i}": _id})
                )
        return Email.objects.filter(pk=self.pk)

    @staticmethod
    def text2html(plain):
        content = html.escape(plain).replace("\n", "<br/>")
        return f"<div>{content}</div>"

    @staticmethod
    def html2text(html):
        text_maker = html2text.HTML2Text()
        text_maker.ignore_links = True
        return text_maker.handle(html).strip()

    @classmethod
    def make_text_content(cls, email_message, reply_to_obj=None, find_reply_to=True):
        """
        Parse email contents and extract out text, removing content from an
        email being replied to.

        Because different email clients format replies differently, we try to
        match against alpha characters only when filtering out the replied to
        message. Additionally, we try to detect and remove a date line before
        the quoted text (On DATE, PERSON wrote:).
        """
        text_content = None
        html_content = None
        html = email_message.get_body("html")
        if html is not None:
            html_content = html.get_content()
            text_content = Email.html2text(html_content)
        if text_content is None:
            plain = email_message.get_body("plain")
            if plain is not None:
                text_content = plain.get_content()
        if text_content is None:
            return (None, None)
        # remove instances of "mailto:" links if any appear raw
        text_content = re.sub(r"\bmailto:", r"", text_content)
        if find_reply_to and reply_to_obj is None:
            in_reply_to_id = cls.parseaddr(email_message.get("In-Reply-To"))
            if in_reply_to_id is not None:
                reply_to_obj = (
                    Email.objects.filter(message_id=in_reply_to_id)
                    .only(
                        "text_content",
                        "header_content",
                        "from_address",
                    )
                    .first()
                )
        if reply_to_obj is not None:
            reply_to_email_message = email.message_from_bytes(
                reply_to_obj.raw_content,
                policy=email.policy.default,
            )
            reply_to_all_text_content, _ = Email.make_text_content(
                reply_to_email_message, find_reply_to=False
            )
            if reply_to_all_text_content is not None:
                full_from_address = reply_to_obj.headers().get("From")
                lines = text_content.split("\n")
                line_letters = [
                    "".join(c.lower() for c in line if c.isalpha()) for line in lines
                ]
                line_starts = {}
                length = 0
                for i, line in enumerate(line_letters):
                    line_starts[length] = i
                    length += len(line)
                line_starts[length] = len(line_letters)
                letters = "".join(line_letters)
                reply_to_letters = "".join(
                    c.lower() for c in reply_to_all_text_content if c.isalpha()
                )
                last_match = len(letters)
                if reply_to_letters:
                    while last_match != -1:
                        last_match = letters.rfind(reply_to_letters, 0, last_match)
                        start_line = line_starts.get(last_match)
                        end_line = line_starts.get(last_match + len(reply_to_letters))
                        if start_line is not None and end_line is not None:
                            while start_line and not line_letters[start_line - 1]:
                                start_line -= 1
                            if start_line:
                                # check for a "On [DATE], [SENDER] wrote:" line
                                line = lines[start_line - 1]
                                realname, address = email.utils.parseaddr(
                                    full_from_address
                                )
                                for address_part in (address, realname):
                                    if address_part is not None:
                                        line = line.replace(address_part, "")
                                try:
                                    _, tokens = dateutil.parser.parse(
                                        line, fuzzy_with_tokens=True
                                    )
                                except ValueError:
                                    pass
                                else:
                                    line = " ".join(tokens)
                                has_only_filler_words = True
                                line = "".join(
                                    c.lower() if c.isalpha() else " " for c in line
                                )
                                for word in line.split():
                                    if word not in (
                                        "on",
                                        "at",
                                        "wrote",
                                    ):
                                        has_only_filler_words = False
                                if has_only_filler_words:
                                    start_line -= 1
                                    while (
                                        start_line and not line_letters[start_line - 1]
                                    ):
                                        start_line -= 1
                            text_content = "\n".join(
                                lines[:start_line] + lines[end_line:]
                            )
                            break
        return (text_content.strip(), html_content)

    @classmethod
    def get_unsubscribe_link(cls, message_id):
        return generate_url(
            "prehunt", f"/unsubscribe?mid={cls.parseaddr(message_id).split('@')[0]}"
        )

    # these methods are somewhat hunt / discord specific
    def created_discord_message(self):
        email_answer_url = generate_url(
            "internal", "/spoilr/emails/", {"email": self.pk}
        )
        if self.team:
            _from = f"{self.team} ({self.from_address})"
        else:
            _from = f"{self.from_address}"
        return (
            f"Email #{self.pk} sent by {_from}\n"
            f"**Subject:** ```{self.subject[:1500]}```\n"
            f"**Question:** ```{self.text_content[:1500]}```\n"
            f"**Claim email reply:** {email_answer_url}\n"
        )

    def claimed_discord_message(self, claimer):
        return f"Email #{self.pk} [{self.subject}] claimed by {claimer}"

    def unclaimed_discord_message(self):
        return f"Email #{self.pk} [{self.subject}] was unclaimed"

    @classmethod
    def responded_discord_message(cls, email_request, email_response=None):
        if email_request.team:
            _from = f"{email_request.team} ({email_request.from_address})"
        else:
            _from = f"{email_request.from_address}"
        if email_request.status == Email.RECEIVED_NO_REPLY_REQUIRED:
            response_text = "(No response required)"
        elif email_response is None:
            response_text = "(email_response was unexpectedly None, check logs)"
        else:
            response_text = email_response.text_content

        return (
            f"Email #{email_request.pk} resolved by {email_request.handler}\n"
            f"Email was requested by {_from}\n"
            f"**Subject:** ```{email_request.subject[:1500]}```\n"
            f"**Request:** ```{email_request.text_content[:1500]}```\n"
            f"**Response:** {response_text}\n"
        )

    class Meta:
        unique_together = (
            ("uidvalidity", "uid"),
            # Same team should not receive multiple of the same canned email
            ("team", "canned_template"),
        )
        ordering = ["-received_datetime"]
