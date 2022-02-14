from django.contrib.auth.forms import SetPasswordForm
from django.forms import Form, fields


class RequestResetForm(Form):
    username = fields.CharField(min_length=1, required=True)


class ValidateTokenForm(Form):
    username = fields.CharField(min_length=1, required=True)
    token = fields.CharField(min_length=1, required=True)


class ResetPasswordForm(SetPasswordForm):
    pass
