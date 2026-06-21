from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class SignInView(APIView):
    """
    POST /api/auth/signin/

    Authenticates a user with email + password and returns a JWT token pair.

    Request body:
        {
            "email": "user@example.com",
            "password": "secret123"
        }

    Response 200:
        {
            "id": 1,
            "email": "user@example.com",
            "access": "<JWT access token>",
            "refresh": "<JWT refresh token>"
        }

    Response 401:
        { "detail": "Invalid credentials." }

    Authentication on subsequent requests:
        Add the header:
            Authorization: Bearer <access token>
    """

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Django's authenticate() uses the USERNAME_FIELD (email) for lookup
        user = authenticate(request, username=email, password=password)

        if user is None:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "This account is inactive."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )
