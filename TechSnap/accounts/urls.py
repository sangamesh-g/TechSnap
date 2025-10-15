from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path('', views.home_view, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path("profile/", views.profile_settings, name="profile_settings"),
    path('logout/', views.logout_view, name='logout'),
    path('choose/', views.choose_action, name='choose_action'),
    path('invitations/', views.invitations_view, name='invitations'),
]
