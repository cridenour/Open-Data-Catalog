from django import forms

from registration.backends.default.views import RegistrationView
# from registration.backends.default import DefaultBackend
from registration.forms import RegistrationForm, RegistrationFormUniqueEmail
from django.db import transaction
from django.contrib.auth.models import Group
from OpenDataCatalog.opendata.models import ODPUserProfile
from widgets import *
from fields import *


class ODPRegistrationForm(RegistrationForm):

    first_name = forms.RegexField(regex=r'^\w', max_length=30, widget=forms.TextInput(), label="First Name",
                                error_messages={ 'invalid': "This value must contain only letters" }, required=True)
    last_name = forms.RegexField(regex=r'^\w', max_length=30, widget=forms.TextInput(), label="Last Name",
                                error_messages={ 'invalid': "This value must contain only letters" }, required=True)
    organization = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'placeholder': 'Optional'}))
    can_notify = forms.BooleanField(
        required=False,
        label="",
        help_text="Would you like to receive e-mail updates regarding OpenDataCincy?"
    )
    recaptcha = ReCaptchaField(label="")


class CatalogRegistrationView(RegistrationView):
    """Custom registration view that uses our custom form."""

    form_class = ODPRegistrationForm

    @transaction.commit_on_success
    def register(self, request, **cleaned_data):
        """
        Creates the new user and their profile
        """
        new_user = super(CatalogRegistrationView, self).register(request, **cleaned_data)
        new_user.first_name = cleaned_data['first_name']
        new_user.last_name = cleaned_data['last_name']

        try:
            group = Group.objects.get(name='Public Users')
            new_user.groups.add(group)
        except Group.DoesNotExist:
            pass

        new_user.save()

        # Create Open Data user profile
        profile = ODPUserProfile()
        profile.user = new_user
        profile.organization = cleaned_data['organization']
        profile.can_notify = cleaned_data['can_notify']
        profile.save()

        return new_user
