# organization/urls.py
from django.urls import path
from . import views

app_name = "organizations"

urlpatterns = [
    path("create/", views.create_organization, name="create"),
    path("dashboard/<uuid:org_uuid>/", views.dashboard, name="dashboard"),
    path("invite/<uuid:org_uuid>/", views.invite_create, name="invite_create"),
    path("accept/<uuid:token>/", views.accept_invite, name="accept_invite"),
    path("join/", views.join_by_uuid, name="join_by_uuid"),
    path("<uuid:org_uuid>/member/<int:member_id>/update-role/", views.update_member_role, name="update_member_role"),
    path("<uuid:org_uuid>/leave/", views.leave_organization, name="leave_organization"),
]
