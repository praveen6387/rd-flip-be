from django.contrib import admin

from rd_flip_be.models import ContactUs


@admin.register(ContactUs)
class ContactUsAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone_number", "created_at")
    search_fields = ("name", "email", "phone_number", "message")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
