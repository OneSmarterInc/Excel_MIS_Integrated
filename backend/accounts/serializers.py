from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "role", "date_joined"]
        read_only_fields = ["id", "role", "date_joined"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["name", "email", "password", "role"]

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("That email is already registered.")
        return value

    def validate_role(self, value):
        if value not in dict(User.Role.choices):
            raise serializers.ValidationError("Role must be FACULTY or STUDENT.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)

    def validate(self, attrs):
        user = authenticate(
            username=attrs["email"].lower().strip(), password=attrs["password"]
        )
        if user is None:
            raise serializers.ValidationError("Email or password is incorrect.")
        wanted = attrs.get("role")
        if wanted and user.role != wanted:
            raise serializers.ValidationError(
                f"This account is registered as {user.get_role_display()}."
            )
        attrs["user"] = user
        return attrs


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    }
