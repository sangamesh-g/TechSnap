# organization/forms.py
from django import forms
from .models import Organization, Invite, ROLE_CHOICES

INPUT_CLASS = "w-full px-3 py-2 border rounded focus:outline-none focus:ring"

class OrganizationCreateForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name", "campus"]
        widgets = {
            "name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Organization name"}),
            "campus": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Mallareddy campus"}),
        }


class InviteForm(forms.ModelForm):
    class Meta:
        model = Invite
        fields = ["email", "role"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "border p-2 rounded w-full"}),
            "role": forms.Select(attrs={"class": "border p-2 rounded w-full"}),
        }

class JoinOrgByUUIDForm(forms.Form):
    org_uuid = forms.UUIDField(widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "Paste org UUID"}))
