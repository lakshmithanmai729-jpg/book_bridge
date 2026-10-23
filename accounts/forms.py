"""Forms for signing up and signing in.

Both forms are deliberately forgiving.  On a phone the keyboard starts with a
capital letter, autocorrect likes to "fix" usernames, and a slow tap can fire
the submit button twice.  All three used to end in a confusing
"That username already exists" page for somebody who had just created the
account themselves, so every field here is normalised and both forms explain
what to do next.
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

# Shared by every text field on the two auth screens: phones must not
# capitalise, autocorrect or spell-check a username or an email address.
PLAIN_TEXT = {
    'autocapitalize': 'none',
    'autocorrect': 'off',
    'autocomplete': 'off',
    'spellcheck': 'false',
}


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        # Without ``email`` here the ModelForm silently drops it and the member
        # is saved with no address — password reset could then never find them.
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Django 5.1+ adds an unusable-password checkbox we never want to show.
        self.fields.pop('usable_password', None)

        username = self.fields['username']
        username.widget.attrs.update(PLAIN_TEXT)
        username.widget.attrs.update({
            'autocomplete': 'username',
            'placeholder': 'e.g. sirisha98',
        })

        email = self.fields['email']
        email.widget.attrs.update(PLAIN_TEXT)
        email.widget.attrs.update({
            'autocomplete': 'email',
            'inputmode': 'email',
            'placeholder': 'you@example.com',
        })

        for name in ('password1', 'password2'):
            self.fields[name].widget.attrs.update({
                'autocapitalize': 'none',
                'spellcheck': 'false',
            })

        # Filled in by clean_username / clean_email so the view can offer a
        # "sign in instead" button, and so a repeated submit can be treated as
        # a sign-in when the password matches.
        self.existing_user = None
        self.existing_email_user = None

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()

        if not username:
            raise forms.ValidationError('Choose a username so buyers can find you.')

        # Compare without case: "Sirisha98" and "sirisha98" are the same person
        # on a phone that capitalises the first letter.
        existing = User.objects.filter(username__iexact=username).first()
        if existing is not None:
            self.existing_user = existing
            raise forms.ValidationError(
                'This username already has an account. Sign in below — or choose '
                'a different username.'
            )

        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()

        existing = User.objects.filter(email__iexact=email).exclude(email='').first() if email else None
        if existing is not None:
            self.existing_email_user = existing
            raise forms.ValidationError(
                'This email is already registered. Sign in instead — or use a '
                'different email address.'
            )

        return email


class SignInForm(AuthenticationForm):
    """Login form that ignores stray spaces and capital letters.

    Django's built-in backend matches the username exactly, so somebody who
    signed up as ``sirisha98`` could not log in from a phone that typed
    ``Sirisha98``.  We look the account up case-insensitively (and trimmed)
    before handing the credentials to Django.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update(PLAIN_TEXT)
        self.fields['username'].widget.attrs.update({
            'autocomplete': 'username',
            'placeholder': 'your username',
        })
        self.fields['password'].widget.attrs.update({
            'autocapitalize': 'none',
            'spellcheck': 'false',
            'autocomplete': 'current-password',
        })

    def clean_username(self):
        return (self.cleaned_data.get('username') or '').strip()

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password and not User.objects.filter(username=username).exists():
            match = User.objects.filter(username__iexact=username).first()
            if match is not None:
                # Same person, different capitalisation — log them into the
                # account that actually exists.
                self.cleaned_data['username'] = match.username

        return super().clean()
