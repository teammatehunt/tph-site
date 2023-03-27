import spoilr.hints.models

from django import forms


class AnswerHintForm(forms.ModelForm):
    # Hide the "No response" from the answer form.
    status = forms.ChoiceField(
        choices=list(spoilr.hints.models.Hint.STATUSES.items())[1:]
    )
    hint_request_id = forms.IntegerField(
        widget=forms.HiddenInput,
    )

    class Meta:
        model = spoilr.hints.models.Hint
        fields = ["text_content", "status"]
        widgets = {
            "text_content": forms.Textarea(
                attrs={"placeholder": "Enter your response here"}
            ),
        }
