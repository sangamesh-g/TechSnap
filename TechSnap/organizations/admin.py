# organization/admin.py
from django.contrib import admin
from .models import Organization, Membership, Invite

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "uuid", "created_by", "created_at")
    search_fields = ("name", "uuid", "campus")
    readonly_fields = ("uuid",)

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "org", "role", "is_active", "joined_at")
    list_filter = ("role", "is_active")

@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ("email", "org", "role", "invited_by","payment", "accepted", "created_at", "expires_at")
    search_fields = ("email",)
