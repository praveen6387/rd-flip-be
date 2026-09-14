from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
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


class Plan(models.Model):
    PLAN_TYPE_CHOICES = [
        ("studio", "Studio"),
        ("lab", "Lab"),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    credit = models.PositiveIntegerField()
    validity_days = models.PositiveIntegerField()
    features = ArrayField(
        models.TextField(),
        default=list,
        blank=True,
        help_text="List of text items describing this plan",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "plans"
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} - {self.plan_type}"


class UserPlan(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
    ]

    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_plans",
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="user_plans",
    )

    start_date = models.DateTimeField()
    expiry_date = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.UUIDField(null=True, blank=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "user_plans"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"


class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    id = models.AutoField(primary_key=True)

    order_name = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        db_index=True,
    )

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    user_plan = models.ForeignKey(
        UserPlan,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending",
    )

    gateway_order_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    created_by = models.UUIDField(
        null=True,
        blank=True,
    )
    updated_by = models.UUIDField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_name


class PaymentTransaction(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    id = models.AutoField(primary_key=True)

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="payment_transactions",
    )

    gateway_payment_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )

    gateway_signature = models.TextField(
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
    )

    payment_method = models.CharField(
        max_length=50,
        blank=True,
    )

    gateway_response = models.JSONField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "payment_transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return self.gateway_payment_id


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

    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    facebook_url = models.URLField(blank=True, null=True)

    total_pages = models.PositiveIntegerField(default=0)
    flip_id = models.CharField(max_length=20, unique=True, db_index=True, editable=False)

    active_until = models.DateTimeField(null=True, blank=True)

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

    image_url = models.URLField(max_length=2048, blank=True)
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


class CreditTransaction(models.Model):
    CREDIT_TYPE_CHOICES = [
        ("free", "Free"),
        ("purchase", "Purchase"),
        ("usage", "Usage"),
        ("expiry", "Expiry"),
        ("refund", "Refund"),
        ("adjustment", "Adjustment"),
    ]

    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="credit_transactions",
    )

    credit_type = models.CharField(
        max_length=20,
        choices=CREDIT_TYPE_CHOICES,
    )

    credits = models.IntegerField()

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="credit_transactions",
        null=True,
        blank=True,
    )

    flipbook = models.ForeignKey(
        Flipbook,
        on_delete=models.PROTECT,
        related_name="credit_transactions",
        null=True,
        blank=True,
    )

    expiry_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by = models.UUIDField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "credit_transactions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.credits} credits"


class Setting(models.Model):
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "settings"

    def __str__(self):
        return self.key


class ContactUs(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contact_us"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} <{self.email}>"
