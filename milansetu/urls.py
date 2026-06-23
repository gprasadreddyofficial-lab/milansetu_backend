from django.urls import path

from .views import (
    IdealPartnerView,
    MyProfileView,
    ProfileDetailsDetailView,
    ProfileDetailsListView,
    SentInterestDetailView,
    SentInterestListView,
    SentInterestStatsView,
    SignupView,
)
from .gallery_views import (
    UserGalleryDetailView,
    UserGalleryImageView,
    UserGalleryListView,
    UserGallerySetProfileView,
)

app_name = "milansetu"

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("profile/fetch_detail/", MyProfileView.as_view(), name="my-profile"),
    path("ideal-partner/", IdealPartnerView.as_view(), name="ideal-partner"),
    path("profiles/", ProfileDetailsListView.as_view(), name="profile-list"),
    path("profiles/<int:pk>/", ProfileDetailsDetailView.as_view(), name="profile-detail"),
    path("interests/sent/", SentInterestListView.as_view(), name="sent-interests"),
    path("interests/sent/stats/", SentInterestStatsView.as_view(), name="sent-interests-stats"),
    path("interests/sent/<int:pk>/", SentInterestDetailView.as_view(), name="sent-interest-detail"),
    path("gallery/", UserGalleryListView.as_view(), name="gallery-list"),
    path("gallery/<int:pk>/", UserGalleryDetailView.as_view(), name="gallery-detail"),
    path("gallery/<int:pk>/set-profile/", UserGallerySetProfileView.as_view(), name="gallery-set-profile"),
    path("gallery/<int:pk>/image/", UserGalleryImageView.as_view(), name="gallery-image"),
]
