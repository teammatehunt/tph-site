import spoilr.email.models
from django import forms


class AnswerEmailForm(forms.ModelForm):
    # primary key id (as opposed to Message-Id)
    email_in_reply_to_pk = forms.IntegerField(
        widget=forms.HiddenInput,
    )
    ACTION_NO_REPLY = "no-reply"
    ACTION_SUBMIT = "submit"
    # Add actions here for custom puzzle email responses.

    class Meta:
        model = spoilr.email.models.Email
        fields = ["text_content"]
        widgets = {
            "text_content": forms.Textarea(
                attrs={
                    "placeholder": "Enter your reply here",
                    "cols": False,
                    "rows": False,
                }
            ),
        }

    def clean(self):
        action = self.data.get("action")
        cd = self.cleaned_data
        text = cd.get("text_content", "")
        stripped_text = text.strip()
        resolved_without_reply = action == self.ACTION_NO_REPLY
        if resolved_without_reply:
            if stripped_text:
                self.add_error(
                    field=None, error="Cannot autoresolve while text is nonempty."
                )
        elif action == self.ACTION_SUBMIT:
            # sending
            if not stripped_text:
                self.add_error(field=None, error="Cannot send empty email.")
        else:
            self.add_error(field=None, error="Valid action was not specified.")
        return cd
