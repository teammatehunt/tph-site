from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from spoilr.core.models import UserTeamRole
from spoilr.registration.models import IndividualRegistrationInfo, TeamRegistrationInfo

from puzzles.models import ExtraGuessGrant, Team


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = UserCreationForm.Meta.fields


class TeamCreationForm(forms.ModelForm):
    class Meta:
        model = TeamRegistrationInfo
        exclude = ["team"]

    # Set the team role to a shared user; assign the team to the reg info.
    def save(self, user):
        team = Team(username=user.username, name=self.cleaned_data["team_name"])
        team.save()

        user.team_role = UserTeamRole.SHARED_ACCOUNT
        user.team = team
        user.save()

        team_registration_info = super().save(commit=False)
        team_registration_info.team = team
        team_registration_info.save()

        return team


class TeamEditForm(forms.ModelForm):
    class Meta:
        model = TeamRegistrationInfo
        exclude = ["team"]


class IndividualCreationForm(forms.ModelForm):
    class Meta:
        model = IndividualRegistrationInfo
        exclude = ["user"]

    # Associate the user with the individual registration info.
    def save(self, user):
        individual_registration_info = super().save(commit=False)
        individual_registration_info.user = user
        individual_registration_info.save()

        return individual_registration_info


class IndividualEditForm(forms.ModelForm):
    class Meta:
        model = IndividualRegistrationInfo
        exclude = ["user"]


class RequestHintForm(forms.Form):
    text_content = forms.CharField(
        label=(
            "Describe everything you've tried on this puzzle. We will "
            "provide a hint to help you move forward. The more detail you "
            "provide, the less likely it is that we'll tell you "
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
        notif_choices = [
            (team.team_email, "Team Captain"),
            ("all", "Everyone"),
            ("none", "No one"),
        ]
        self.fields["notify_emails"] = forms.ChoiceField(
            label="When the hint is answered, send an email to:", choices=notif_choices
        )


class ExtraGuessGrantForm(forms.ModelForm):
    class Meta:
        model = ExtraGuessGrant
        fields = ["extra_guesses"]


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
