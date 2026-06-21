from django.urls import path

from .views import (
    MyProfileView,
    ProfileDetailsDetailView,
    ProfileDetailsListView,
    SignupView,
)

app_name = "milansetu"

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    # GET  — returns CSRF token for the client
    # POST — register new user, returns JWT access + refresh tokens
    path("signup/", SignupView.as_view(), name="signup"),

    # ── Authenticated user's own profile ─────────────────────────────────────
    # GET   — fetch my profile
    # PATCH — edit my profile (partial, recommended)
    # PUT   — replace my profile (full)
    path("profile/me/", MyProfileView.as_view(), name="my-profile"),

    # ── Admin: all profiles ───────────────────────────────────────────────────
    # GET  — list all profiles
    # POST — create a profile entry
    path("profiles/", ProfileDetailsListView.as_view(), name="profile-list"),

    # GET / PUT / PATCH / DELETE a specific profile by PK
    path("profiles/<int:pk>/", ProfileDetailsDetailView.as_view(), name="profile-detail"),
]
