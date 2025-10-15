# organization/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.core.mail import send_mail
from django.conf import settings
from pytz import timezone as pytz_timezone
from payments.models import Payment
from .models import Organization, Membership, Invite, ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER ,ROLE_CREATOR
from .forms import OrganizationCreateForm, InviteForm, JoinOrgByUUIDForm
import razorpay

def _user_has_role(user, org, roles):
    return Membership.objects.filter(user=user, org=org, role__in=roles, is_active=True).exists()

def _send_invite_email(request, invite):
    accept_url = request.build_absolute_uri(
        reverse("organizations:accept_invite", args=[str(invite.token)])
    )
    login_url = request.build_absolute_uri(reverse("accounts:login"))
    register_url = request.build_absolute_uri(reverse("accounts:signup"))

    subject = f"Invite to join {invite.org.name}"
    message = (
        f"Hello,\n\n"
        f"You have been invited to join the organization '{invite.org.name}' "
        f"as {invite.get_role_display()}.\n\n"
        f"👉 Accept Invitation: {accept_url}\n\n"
        f"If you don't yet have an account:\n"
        f"   • Register here: {register_url}\n"
        f"   • Already have an account? Login here: {login_url}\n\n"
        f"Once you log in or register using this email, the invite will be automatically applied.\n\n"
        f"Best regards,\n"
        f"{invite.org.name} Team"
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [invite.email],
        fail_silently=False
    )
    

@login_required
def create_organization(request):
    if request.method == "POST":
        form = OrganizationCreateForm(request.POST)
        if form.is_valid():
            org = form.save(commit=False)
            org.created_by = request.user
            org.save()
            # make creator owner
            Membership.objects.create(user=request.user, org=org, role=ROLE_OWNER)
            messages.success(request, f"Organizations '{org.name}' created.")
            return redirect("organizations:dashboard", org_uuid=org.uuid)
    else:
        form = OrganizationCreateForm()
    return render(request, "organizations/create.html", {"form": form})



IST = pytz_timezone("Asia/Kolkata")

@login_required
def dashboard(request, org_uuid):
    org = get_object_or_404(Organization, uuid=org_uuid)
    membership = Membership.objects.filter(user=request.user, org=org, is_active=True).first()
    if not membership:
        return HttpResponseForbidden("You are not a member of this organization.")

    members = org.memberships.select_related("user")

    # Handle Invite POST
    if request.method == "POST":
        invite_form = InviteForm(request.POST)
        if invite_form.is_valid():
            invite = invite_form.save(commit=False)
            invite.org = org
            invite.invited_by = request.user
            invite.save()
            _send_invite_email(request, invite)
            messages.success(request, f"Invite sent to {invite.email}")
            return redirect("organizations:dashboard", org_uuid=org.uuid)
    else:
        invite_form = InviteForm()

    invites_by_email = {invite.email: invite for invite in org.invites.all()}

    # Add invite time in IST
    from pytz import timezone as pytz_timezone
    IST = pytz_timezone("Asia/Kolkata")
    for m in members:
        invite = invites_by_email.get(m.user.email)
        if invite:
            m.invite_created_at = invite.created_at.astimezone(IST)
        else:
            m.invite_created_at = None

    admin_roles = [ROLE_OWNER, ROLE_ADMIN]
    creator_roles = [ROLE_CREATOR, ROLE_MEMBER]

    context = {
        "org": org,
        "membership": membership,
        "members": members,
        "invite_form": invite_form,
        "invites_by_email": invites_by_email,
        "admin_roles": admin_roles,
        "creator_roles": creator_roles,
    }
    return render(request, "organizations/dashboard.html", context)

@login_required
def invite_create(request, org_uuid):
    org = get_object_or_404(Organization, uuid=org_uuid)
    if not _user_has_role(request.user, org, ['owner', 'admin']):
        return HttpResponseForbidden("Only owners or admins can invite users.")
    
    if request.method == "POST":
        form = InviteForm(request.POST)
        if form.is_valid():
            invite = form.save(commit=False)
            invite.org = org
            invite.invited_by = request.user
            invite.save()

            # Create a payment for the invite
            payment = Payment.objects.create(
                amount=500,
                status="created",
                description=f"Payment for joining {org.name}",
                user_email=invite.email
            )
            invite.payment = payment
            invite.save()

            _send_invite_email(request, invite)
            messages.success(request, f"Invitation sent to {invite.email}.")
            return redirect("organizations:dashboard", org_uuid=org.uuid)
    
    return redirect("organizations:dashboard", org_uuid=org.uuid)


def accept_invite(request, token):
    invite = get_object_or_404(Invite, token=token)
    if not invite.is_valid():
        messages.error(request, "Invite is expired or already used.")
        return redirect("accounts:login")
    if request.user.is_authenticated:
        if invite.payment and invite.payment.status == "paid":
            try:
                invite.accept(request.user)
                messages.success(request, f"You joined {invite.org.name}.")
                return redirect("organizations:dashboard", org_uuid=invite.org.uuid)
            except Exception as exc:
                messages.error(request, str(exc))
                return redirect("accounts:dashboard")
        else:
            return redirect("payments:process_payment", token=token)
    else:
        signup_url = reverse("accounts:signup")
        return redirect(f"{signup_url}?invite_token={invite.token}&email={invite.email}")


@login_required
def join_by_uuid(request):
    if request.method == "POST":
        form = JoinOrgByUUIDForm(request.POST)
        if form.is_valid():
            org_uuid = form.cleaned_data["org_uuid"]
            org = get_object_or_404(Organization, uuid=org_uuid)
            # Simple: allow direct join as member (you can change to request-for-approval)
            membership, created = Membership.objects.get_or_create(user=request.user, org=org, defaults={"role": ROLE_MEMBER})
            if created:
                messages.success(request, f"You joined {org.name}.")
            else:
                messages.info(request, f"You are already a member of {org.name}.")
            return redirect("organizations:dashboard", org_uuid=org.uuid)
    else:
        form = JoinOrgByUUIDForm()
    return render(request, "organizations/join_by_uuid.html", {"form": form})

@login_required
def leave_organization(request, org_uuid):
    org = get_object_or_404(Organization, uuid=org_uuid)
    membership = Membership.objects.filter(user=request.user, org=org).first()

    if not membership:
        messages.error(request, "You are not a member of this organization.")
        return redirect("accounts:choose_action")

    if membership.role == ROLE_OWNER:
        messages.error(request, "Owner cannot leave the organization. Transfer ownership first.")
        return redirect("organizations:dashboard", org_uuid=org.uuid)

    membership.delete()
    messages.success(request, f"You left {org.name}.")
    return redirect("accounts:choose_action")


@login_required
def update_member_role(request, org_uuid, member_id):
    org = get_object_or_404(Organization, uuid=org_uuid)
    acting_membership = Membership.objects.filter(user=request.user, org=org).first()

    if not acting_membership or acting_membership.role != ROLE_OWNER:
        return HttpResponseForbidden("Only owner can change roles.")

    member = get_object_or_404(Membership, id=member_id, org=org)
    
    new_role = request.POST.get("role")
    if new_role not in [ROLE_ADMIN, ROLE_CREATOR, ROLE_MEMBER, ROLE_OWNER]:
        messages.error(request, "Invalid role.")
        return redirect("organizations:dashboard", org_uuid=org.uuid)

    # ✅ Enforce one owner rule
    if new_role == ROLE_OWNER:
        existing_owner = Membership.objects.filter(org=org, role=ROLE_OWNER).exclude(id=member.id).first()
        if existing_owner:
            messages.error(request, "Only one owner is allowed per organization.")
            return redirect("organizations:dashboard", org_uuid=org.uuid)

    member.role = new_role
    member.save()
    messages.success(request, f"{member.user.email} is now {new_role}.")
    return redirect("organizations:dashboard", org_uuid=org.uuid)
