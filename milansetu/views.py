from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializers import SignupSerializer

from .gallery_service import save_gallery_image
from .matching import (
    apply_employee_filters,
    calculate_compatibility,
    filter_profiles_for_user,
)
from .models import IdealPartner, ProfileDetails, SentInterest
from .premium import (
    can_edit_profile,
    check_premium_ideal_partner_fields,
    get_account_meta,
    increment_profile_edit_count,
)
from .serializers import (
    IdealPartnerSerializer,
    ProfileDetailsSerializer,
    SentInterestCreateSerializer,
    SentInterestSerializer,
)


def _get_or_create_ideal_partner(user) -> IdealPartner:
    ideal, _ = IdealPartner.objects.get_or_create(user=user)
    return ideal


def _account_response(user, profile=None, ideal=None) -> dict:
    return {
        "profile": ProfileDetailsSerializer(profile).data if profile else None,
        "ideal_partner": IdealPartnerSerializer(ideal).data if ideal else None,
        "account": get_account_meta(user),
    }


# ─── Signup ───────────────────────────────────────────────────────────────────

@method_decorator(ensure_csrf_cookie, name="dispatch")
class SignupView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        return Response({"csrfToken": get_token(request)}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        uploaded = request.FILES.get("profile_photo") or request.FILES.get("image")
        if uploaded:
            try:
                save_gallery_image(user, uploaded, set_as_profile=True)
            except ValueError as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "user_type": user.user_type,
                "is_premium": user.is_premium,
                "is_staff": user.is_staff,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_201_CREATED,
        )


# ─── My Profile + Ideal Partner ───────────────────────────────────────────────

class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_profile(self, user):
        try:
            return ProfileDetails.objects.get(user=user)
        except ProfileDetails.DoesNotExist:
            return None

    def get(self, request):
        profile = self._get_profile(request.user)
        ideal = IdealPartner.objects.filter(user=request.user).first()
        if profile is None:
            return Response(
                {
                    **_account_response(request.user, profile=None, ideal=ideal),
                    "detail": "Profile not found. Use PATCH to create one.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(_account_response(request.user, profile=profile, ideal=ideal))

    def patch(self, request):
        allowed, error_msg = can_edit_profile(request.user)
        if not allowed:
            return Response(
                {"detail": error_msg, "upgrade_required": True},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        profile = self._get_profile(request.user)
        if profile is None:
            serializer = ProfileDetailsSerializer(data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            profile = serializer.save(user=request.user)
            increment_profile_edit_count(request.user)
        else:
            serializer = ProfileDetailsSerializer(profile, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            profile = serializer.save()
            increment_profile_edit_count(request.user)

        ideal = _get_or_create_ideal_partner(request.user)
        return Response(_account_response(request.user, profile=profile, ideal=ideal))

    def put(self, request):
        return self.patch(request)


class IdealPartnerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ideal = IdealPartner.objects.filter(user=request.user).first()
        if ideal is None:
            return Response(
                {"detail": "No ideal partner preferences yet. Use PATCH to set them."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "ideal_partner": IdealPartnerSerializer(ideal).data,
                "account": get_account_meta(request.user),
            }
        )

    def patch(self, request):
        ideal = _get_or_create_ideal_partner(request.user)
        payload, blocked, premium_error = check_premium_ideal_partner_fields(
            request.user, request.data
        )

        if premium_error:
            return Response(
                {
                    "detail": premium_error,
                    "upgrade_required": True,
                    "premium_fields": blocked,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        serializer = IdealPartnerSerializer(ideal, data=payload, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        ideal = serializer.save()
        return Response(
            {
                "ideal_partner": IdealPartnerSerializer(ideal).data,
                "account": get_account_meta(request.user),
            }
        )


# ─── Profile discovery (role-based) ─────────────────────────────────────────

class ProfileDetailsListView(APIView):
    """
    GET /api/milansetu/profiles/

    - user: profiles matching ideal partner preferences (sorted by score)
    - employee/admin: all profiles with optional query filters
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        base_qs = (
            ProfileDetails.objects.filter(user__isnull=False)
            .exclude(user=request.user)
            .select_related("user")
        )

        if request.user.is_employee:
            profiles = list(apply_employee_filters(base_qs, request.query_params))
            data = []
            for profile in profiles:
                row = ProfileDetailsSerializer(profile).data
                row["match_score"] = calculate_compatibility(
                    IdealPartner.objects.filter(user=request.user).first(),
                    profile,
                )
                row["user_type"] = profile.user.user_type
                data.append(row)
            return Response(data)

        ideal = IdealPartner.objects.filter(user=request.user).first()
        scored = filter_profiles_for_user(base_qs, ideal)
        data = []
        for profile, score in scored:
            row = ProfileDetailsSerializer(profile).data
            row["match_score"] = score
            data.append(row)
        return Response(data)

    def post(self, request):
        if not request.user.is_superuser:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ProfileDetailsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProfileDetailsDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk):
        try:
            return ProfileDetails.objects.select_related("user").get(pk=pk)
        except ProfileDetails.DoesNotExist:
            return None

    def get(self, request, pk):
        profile = self._get_object(pk)
        if not profile:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if profile.user_id == request.user.id:
            return Response(ProfileDetailsSerializer(profile).data)

        if request.user.is_employee:
            row = ProfileDetailsSerializer(profile).data
            row["match_score"] = calculate_compatibility(
                IdealPartner.objects.filter(user=request.user).first(),
                profile,
            )
            row["user_type"] = profile.user.user_type
            ideal = IdealPartner.objects.filter(user=profile.user).first()
            if ideal:
                row["ideal_partner"] = IdealPartnerSerializer(ideal).data
            return Response(row)

        ideal = IdealPartner.objects.filter(user=request.user).first()
        score = calculate_compatibility(ideal, profile)
        if score < 60:
            return Response({"detail": "Profile not in your match list."}, status=status.HTTP_403_FORBIDDEN)

        row = ProfileDetailsSerializer(profile).data
        row["match_score"] = score
        ideal = IdealPartner.objects.filter(user=profile.user).first()
        if ideal:
            row["ideal_partner"] = IdealPartnerSerializer(ideal).data
        return Response(row)

    def patch(self, request, pk):
        profile = self._get_object(pk)
        if not profile or profile.user_id != request.user.id:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        allowed, error_msg = can_edit_profile(request.user)
        if not allowed:
            return Response(
                {"detail": error_msg, "upgrade_required": True},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        serializer = ProfileDetailsSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        profile = serializer.save()
        increment_profile_edit_count(request.user)
        return Response(ProfileDetailsSerializer(profile).data)

    def put(self, request, pk):
        return self.patch(request, pk)

    def delete(self, request, pk):
        if not request.user.is_superuser:
            return Response({"detail": "Not allowed."}, status=status.HTTP_403_FORBIDDEN)
        profile = self._get_object(pk)
        if not profile:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        profile.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Sent Interests ───────────────────────────────────────────────────────────

class SentInterestListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        interests = (
            SentInterest.objects.filter(sender=request.user)
            .select_related("receiver_profile")
            .order_by("-created_at")
        )
        return Response(SentInterestSerializer(interests, many=True).data)

    def post(self, request):
        serializer = SentInterestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        receiver_id = serializer.validated_data["receiver_profile_id"]
        try:
            receiver_profile = ProfileDetails.objects.select_related("user").get(pk=receiver_id)
        except ProfileDetails.DoesNotExist:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        if receiver_profile.user_id == request.user.id:
            return Response({"detail": "Cannot send interest to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        if SentInterest.objects.filter(
            sender=request.user,
            receiver_profile=receiver_profile,
        ).exists():
            return Response({"detail": "Interest already sent."}, status=status.HTTP_400_BAD_REQUEST)

        ideal = IdealPartner.objects.filter(user=request.user).first()
        score = calculate_compatibility(ideal, receiver_profile)

        interest = SentInterest.objects.create(
            sender=request.user,
            receiver_profile=receiver_profile,
            message=serializer.validated_data.get("message", ""),
            match_score=score,
        )
        return Response(
            SentInterestSerializer(interest).data,
            status=status.HTTP_201_CREATED,
        )


class SentInterestDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_interest(self, request, pk):
        try:
            return SentInterest.objects.select_related("receiver_profile").get(
                pk=pk,
                sender=request.user,
            )
        except SentInterest.DoesNotExist:
            return None

    def patch(self, request, pk):
        interest = self._get_interest(request, pk)
        if not interest:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        if action == "withdraw":
            if interest.status != SentInterest.Status.PENDING:
                return Response(
                    {"detail": "Only pending interests can be withdrawn."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            interest.status = SentInterest.Status.WITHDRAWN
            interest.save(update_fields=["status", "updated_at"])
            return Response(SentInterestSerializer(interest).data)

        return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        interest = self._get_interest(request, pk)
        if not interest:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        interest.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SentInterestStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = SentInterest.objects.filter(sender=request.user)
        total = qs.count()
        accepted = qs.filter(status=SentInterest.Status.ACCEPTED).count()
        pending = qs.filter(status=SentInterest.Status.PENDING).count()
        declined = qs.filter(status=SentInterest.Status.DECLINED).count()
        response_rate = round((accepted / total) * 100) if total else 0
        return Response(
            {
                "total": total,
                "accepted": accepted,
                "pending": pending,
                "declined": declined,
                "response_rate": response_rate,
            }
        )
