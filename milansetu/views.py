from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import SignupSerializer
from .models import ProfileDetails
from .serializers import ProfileDetailsSerializer


# ─── Signup ───────────────────────────────────────────────────────────────────

@method_decorator(ensure_csrf_cookie, name="dispatch")
class SignupView(APIView):
    """
    GET  /api/milansetu/signup/  — Returns a CSRF token for the client.
    POST /api/milansetu/signup/  — Registers a new user + optional profile
                                   and returns JWT access & refresh tokens.

    Request body (POST):
        {
            "email": "user@example.com",
            "password": "secret123",
            "confirm_password": "secret123",
            "phone": "+919876543210",       // optional
            "full_name": "Ravi Kumar",      // optional profile fields
            ...
        }

    Response 201:
        { "id": 1, "email": "...", "access": "...", "refresh": "..." }
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


# ─── My Profile (authenticated user's own profile) ────────────────────────────

class MyProfileView(APIView):
    """
    GET   /api/milansetu/profile/fetch_detail/  — Retrieve the current user's profile.
    PATCH /api/milansetu/profile/fetch_detail/  — Partially update the current user's profile.
    PUT   /api/milansetu/profile/fetch_detail/  — Fully replace the current user's profile.

    Requires:
        Authorization: Bearer <access token>

    Notes:
        - If no profile exists yet, GET returns 404 with a helpful message.
        - PATCH / PUT will create the profile record if it does not exist yet
          (upsert behaviour) so the client never needs to call a separate
          "create profile" endpoint.
    """

    permission_classes = [IsAuthenticated]

    def _get_or_none(self, user):
        try:
            return ProfileDetails.objects.get(user=user)
        except ProfileDetails.DoesNotExist:
            return None

    def get(self, request):
        profile = self._get_or_none(request.user)
        if profile is None:
            return Response(
                {"detail": "Profile not found. Use PATCH /profile/fetch_detail/ to create one."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProfileDetailsSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        """Partial update — only the fields you send are changed."""
        profile = self._get_or_none(request.user)
        if profile is None:
            # Auto-create on first edit
            serializer = ProfileDetailsSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        serializer = ProfileDetailsSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        """Full update — all non-read-only fields must be provided."""
        profile = self._get_or_none(request.user)
        if profile is None:
            serializer = ProfileDetailsSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        serializer = ProfileDetailsSerializer(profile, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─── Admin: all profiles ──────────────────────────────────────────────────────

class ProfileDetailsListView(APIView):
    """
    GET  /api/milansetu/profiles/   — List all profiles (auth required).
    POST /api/milansetu/profiles/   — Create a standalone profile entry.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profiles = ProfileDetails.objects.all()
        serializer = ProfileDetailsSerializer(profiles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ProfileDetailsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProfileDetailsDetailView(APIView):
    """
    GET    /api/milansetu/profiles/<id>/
    PUT    /api/milansetu/profiles/<id>/
    PATCH  /api/milansetu/profiles/<id>/
    DELETE /api/milansetu/profiles/<id>/
    """

    permission_classes = [IsAuthenticated]

    def _get_object(self, pk):
        try:
            return ProfileDetails.objects.get(pk=pk)
        except ProfileDetails.DoesNotExist:
            return None

    def get(self, request, pk):
        profile = self._get_object(pk)
        if not profile:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProfileDetailsSerializer(profile).data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        profile = self._get_object(pk)
        if not profile:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProfileDetailsSerializer(profile, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        profile = self._get_object(pk)
        if not profile:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProfileDetailsSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        profile = self._get_object(pk)
        if not profile:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
