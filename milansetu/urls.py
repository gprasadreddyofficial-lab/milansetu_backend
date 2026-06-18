from django.urls import path

from .views import ProfileDetailsDetailView, ProfileDetailsListView, SignupView

app_name = "milansetu"

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    # GET  — returns CSRF token for the client
    # POST — register new user, returns JWT access + refresh tokens
    path("signup/", SignupView.as_view(), name="signup"),

    # ── Profile Details ───────────────────────────────────────────────────────
    # GET  — list all profiles
    # POST — create a profile entry
    path("profiles/", ProfileDetailsListView.as_view(), name="profile-list"),

    # GET    — retrieve single profile
    # PUT    — full update
    # PATCH  — partial update
    # DELETE — delete
    path("profiles/<int:pk>/", ProfileDetailsDetailView.as_view(), name="profile-detail"),
]
