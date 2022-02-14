import hashlib

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, validate_email
from django.db.models import Q

from puzzles.hunt_config import TEAM_SIZE
from puzzles.models import Email, ExtraGuessGrant, Hint, Survey, Team, TeamMember


class TeamCreationForm(forms.ModelForm):
    name1 = forms.CharField(max_length=40, required=True)
    name2 = forms.CharField(max_length=40, required=False)
    name3 = forms.CharField(max_length=40, required=False)
    name4 = forms.CharField(max_length=40, required=False)
    name5 = forms.CharField(max_length=40, required=False)
    name6 = forms.CharField(max_length=40, required=False)
    name7 = forms.CharField(max_length=40, required=False)
    name8 = forms.CharField(max_length=40, required=False)

    email1 = forms.EmailField(required=True)
    email2 = forms.EmailField(required=False)
    email3 = forms.EmailField(required=False)
    email4 = forms.EmailField(required=False)
    email5 = forms.EmailField(required=False)
    email6 = forms.EmailField(required=False)
    email7 = forms.EmailField(required=False)
    email8 = forms.EmailField(required=False)

    class Meta:
        model = Team
        fields = ["team_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = None

    def clean(self):
        cleaned_data = super(forms.ModelForm, self).clean()

        emails = []
        for i in range(TEAM_SIZE):
            name_field = f"name{i+1}"
            email_field = f"email{i+1}"
            name = cleaned_data.get(name_field)
            email = cleaned_data.get(email_field)
            if email:
                if not name:
                    self.add_error(name_field, "Name must be provided with email")
                try:
                    emails.append(email)
                    validate_team_member_email_unique(email, team=self.team)
                except forms.ValidationError as err:
                    self.add_error(email_field, err)

        if len(emails) != len(set(emails)):
            raise forms.ValidationError(
                "All of the provided email addresses should be unique"
            )

    def save(self, user):
        team = super().save(commit=False)
        team.user = user
        team.save()

        for i in range(TEAM_SIZE):
            name = self.cleaned_data.get(f"name{i+1}")
            email = self.cleaned_data.get(f"email{i+1}")

            if name:
                TeamMember.objects.create(team=team, name=name, email=email)

        return team


class TeamEditForm(TeamCreationForm):
    class Meta:
        model = Team
        fields = []

    def __init__(self, team, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team


def validate_team_member_email_unique(email, team=None):
    if TeamMember.objects.filter(~Q(team=team), email=email).exists():
        raise forms.ValidationError(
            "Someone with that email is already registered as a member on a "
            "different team."
        )


class SubmitAnswerForm(forms.Form):
    answer = forms.CharField(
        label="Enter your guess:",
        max_length=500,
    )


class RequestHintForm(forms.Form):
    text_content = forms.CharField(
        label=(
            "Describe everything you\u2019ve tried on this puzzle. We will "
            "provide a hint to help you move forward. The more detail you "
            "provide, the less likely it is that we\u2019ll tell you "
            "something you already know."
        ),
        widget=forms.Textarea,
    )
    thread_id = forms.IntegerField(
        widget=forms.HiddenInput,
        required=False,
    )

    def __init__(self, team, *args, **kwargs):
        super(RequestHintForm, self).__init__(*args, **kwargs)
        notif_choices = [("all", "Everyone"), ("none", "No one")]
        notif_choices.extend(team.get_emails(with_names=True))
        self.fields["notify_emails"] = forms.ChoiceField(
            label="When the hint is answered, send an email to:", choices=notif_choices
        )


class AnswerEmailForm(forms.ModelForm):
    # primary key id (as opposed to Message-Id)
    email_in_reply_to_pk = forms.IntegerField(
        widget=forms.HiddenInput,
    )
    ACTION_NO_REPLY = "no-reply"
    ACTION_UNCLAIM = "unclaim"
    # FIXME
    ACTION_CUSTOM_PUZZLE = "custom-puzzle"

    class Meta:
        model = Email
        fields = ["text_content"]

    def clean(self):
        action = self.data.get("action")
        cd = self.cleaned_data
        text = cd.get("text_content", "")
        stripped_text = text.strip()
        unclaimed = action == self.ACTION_UNCLAIM
        resolved_without_reply = action == self.ACTION_NO_REPLY
        custom_puzzle = action == self.ACTION_CUSTOM_PUZZLE
        if resolved_without_reply:
            if stripped_text:
                self.add_error(
                    field=None, error="Cannot autoresolve while text is nonempty."
                )
        elif unclaimed:
            pass
        elif custom_puzzle:
            if stripped_text:
                self.add_error(
                    field=None, error="Cannot populate while text is nonempty."
                )
        else:
            # sending
            if not stripped_text:
                self.add_error(field=None, error="Cannot send empty email.")
        return cd


class AnswerHintForm(forms.ModelForm):
    # Hide the "No response" from the answer form.
    status = forms.ChoiceField(choices=list(Hint.STATUSES.items())[1:])
    hint_request_id = forms.IntegerField(
        widget=forms.HiddenInput,
    )

    class Meta:
        model = Hint
        fields = ["text_content", "status"]


class ExtraGuessGrantForm(forms.ModelForm):
    class Meta:
        model = ExtraGuessGrant
        fields = ["extra_guesses"]


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        exclude = ["team", "puzzle"]


# Redirect on 0 and otherwise redirect to donate page.
class DonationForm(forms.Form):
    amount = forms.DecimalField(label="Amount")


# Allows teams to upload a birthday present (image)
class ProfilePictureForm(forms.ModelForm):
    unsupported_media_type_error_message = (
        "Please upload a valid image of a supported file type (.jpg or .png)."
    )
    profile_pic = forms.ImageField(
        label="profile_pic",
        error_messages={
            "invalid": unsupported_media_type_error_message,
            "invalid_image": unsupported_media_type_error_message,
            "invalid_extension": unsupported_media_type_error_message,
        },
    )
    # We only want to accept JPEG and PNG files. The built-in validator accepts all image files.
    # Passing validators at construction time appends given validators to the list of existing ones,
    # and doing so creates 2 error messages when extension is invalid. Instead we replace the
    # validators list directly to make sure we only have 1 validator.
    profile_pic.validators = [
        FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])
    ]

    def clean_profile_pic(self):
        MAX_WIDTH = 1280
        MAX_HEIGHT = 720
        profile_pic = self.cleaned_data.get("profile_pic", None)
        if not profile_pic:
            # Not supposed to hit this point, but just in case let's add this.
            raise ValidationError("Couldn't read uploaded team photo.")
        width, height = profile_pic.image.size
        if width > MAX_WIDTH:
            raise ValidationError("Team photo was over %d pixels wide." % MAX_WIDTH)
        elif height > MAX_HEIGHT:
            raise ValidationError("Team photo was over %d pixels tall." % MAX_HEIGHT)
        return profile_pic

    class Meta:
        model = Team
        fields = ["profile_pic"]


class UnsubscribeEmailForm(forms.Form):
    email = forms.EmailField(required=True)


class CustomEmailForm(forms.Form):
    subject = forms.CharField(
        label="Subject for your email",
        widget=forms.Textarea,
    )
    html_content = forms.CharField(
        label="The HTML version of your email.",
        widget=forms.Textarea,
    )
    plaintext_content = forms.CharField(
        label="The plaintext version of your email.",
        widget=forms.Textarea,
        required=False,
    )


# Awful, awful hack. Maybe there's a better way.
class HiddenCustomEmailForm(forms.Form):
    subject = forms.CharField(
        label="Subject for your email",
        widget=forms.HiddenInput(),
        initial="",
    )
    html_content = forms.CharField(
        label="The HTML version of your email.",
        widget=forms.HiddenInput(),
        initial="",
    )
    plaintext_content = forms.CharField(
        label="The plaintext version of your email.",
        widget=forms.HiddenInput(),
        initial="",
    )
