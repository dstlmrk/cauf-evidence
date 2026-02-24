from typing import Any

from auditlog.mixins import AuditlogHistoryAdminMixin
from django.contrib import admin
from django.http import HttpRequest
from solo.admin import SingletonModelAdmin

from core.models import AppSettings


class AuditlogMixin(AuditlogHistoryAdminMixin):
    show_auditlog_history_link = True


class ReadOnlyModelAdmin(admin.ModelAdmin):
    """ModelAdmin class that makes model read-only in admin interface"""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
        return False


@admin.register(AppSettings)
class AppSettingsAdmin(SingletonModelAdmin):
    pass
