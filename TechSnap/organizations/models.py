# organization/models.py
from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone
from datetime import timedelta
from payments.models import Payment

# Roles
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_CREATOR = "creator"
ROLE_MEMBER = "member"

ROLE_CHOICES = [
    (ROLE_OWNER, "Owner"),
    (ROLE_ADMIN, "Admin"),
    (ROLE_CREATOR, "Creator"),
    (ROLE_MEMBER, "Member"),
]


class Organization(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    campus = models.CharField(max_length=255, blank=True, null=True)  # Mallareddy campus etc.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.uuid})"


class Membership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "org")
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.user} @ {self.org} as {self.role}"

class Invite(models.Model):
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invites")
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invites"
    )

    payment = models.OneToOneField(
        Payment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    is_accepted = models.BooleanField(default=False)
    accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)  # 7-day expiry
        return super().save(*args, **kwargs)

    def is_valid(self):
        return (not self.accepted) and (
            self.expires_at is None or timezone.now() < self.expires_at
        )

    def accept(self, user):
        if not self.is_valid():
            raise ValueError("Invite is invalid or expired.")
        membership, created = Membership.objects.get_or_create(
            user=user, org=self.org, defaults={"role": self.role}
        )
        self.accepted = True
        self.save()
        return membership

    def __str__(self):
        return f"Invite {self.email} -> {self.org} ({self.role})"
    
    def accept(self, user):
        if not self.is_valid():
            raise ValueError("Invite is invalid or expired.")
        # Require payment to be completed before accepting invite
        if not self.payment or getattr(self.payment, 'status', None) != 'paid':
            raise ValueError("Payment of ₹500 is required to accept this invite.")
        membership, created = Membership.objects.get_or_create(
            user=user, org=self.org, defaults={"role": self.role}
        )
        self.accepted = True
        self.save()
        return membership
