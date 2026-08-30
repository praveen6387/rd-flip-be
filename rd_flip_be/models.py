from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    PLAN_CHOICES = [
        ("studio", "Studio"),
        ("lab", "Lab"),
    ]

    id = models.AutoField(primary_key=True)
    user_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # user info
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    dob = models.DateField(null=True, blank=True)

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=255)

    # studio detals
    studio_name = models.CharField(max_length=255, blank=True)
    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default="studio",
    )

    # social link
    whatsapp_number = models.CharField(max_length=20, blank=True)
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)

    # credits
    total_credit = models.PositiveIntegerField(default=0)
    used_credit = models.PositiveIntegerField(default=0)
    left_credit = models.PositiveIntegerField(default=0)
    expired_credit = models.PositiveIntegerField(default=0)
    credit_expire_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.UUIDField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email


class Flipbook(models.Model):
    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="flipbooks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date = models.DateField()

    studio_name = models.CharField(max_length=255)

    whatsapp_number = models.CharField(max_length=20)
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)

    total_pages = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "flipbooks"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class FlipbookPage(models.Model):
    COVER_TYPE_CHOICES = [
        ("front", "Front"),
        ("middle", "Middle"),
        ("back", "Back"),
    ]

    id = models.AutoField(primary_key=True)

    flipbook = models.ForeignKey(
        Flipbook,
        on_delete=models.CASCADE,
        related_name="pages",
    )
    page_number = models.PositiveIntegerField()

    image_url = models.URLField(blank=True)
    cover_type = models.CharField(max_length=20, choices=COVER_TYPE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "flipbook_pages"
        ordering = ["page_number"]
        unique_together = ("flipbook", "page_number")

    def __str__(self) -> str:
        return f"{self.flipbook.title} — page {self.page_number}"
