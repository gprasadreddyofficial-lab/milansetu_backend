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
    GET  /api/milansetu/signup/  — Returns CSRF token so the client can
                                   attach it before submitting the form.
    POST /api/milansetu/signup/  — Registers a new user + profile,
                                   returns JWT access & refresh tokens.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {"csrfToken": get_token(request)},
            status=status.HTTP_200_OK,
        )

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


# ─── Profile Details ──────────────────────────────────────────────────────────

class ProfileDetailsListView(APIView):
    """
    GET  /api/milansetu/profiles/       — List all profiles (auth required)
    POST /api/milansetu/profiles/       — Create a new profile entry
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
    GET    /api/milansetu/profiles/<id>/   — Retrieve a single profile
    PUT    /api/milansetu/profiles/<id>/   — Full update
    PATCH  /api/milansetu/profiles/<id>/   — Partial update
    DELETE /api/milansetu/profiles/<id>/   — Delete
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
        serializer = ProfileDetailsSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
