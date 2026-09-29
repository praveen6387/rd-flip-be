from django.contrib import admin

from rd_flip_be.models import ContactUs, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "email",
        "first_name",
        "last_name",
        "role",
        "plan",
        "left_credit",
    )
    list_filter = ("role", "plan", "is_active")
    search_fields = ("email", "phone", "first_name", "last_name", "studio_name")
    list_editable = ("role",)
    ordering = ("-created_at",)


@admin.register(ContactUs)
class ContactUsAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone_number", "created_at")
    search_fields = ("name", "email", "phone_number", "message")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
