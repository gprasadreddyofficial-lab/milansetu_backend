from rest_framework import serializers

from .models import ProfileDetails


class ProfileDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfileDetails
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at")
