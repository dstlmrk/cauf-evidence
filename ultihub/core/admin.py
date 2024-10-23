# from typing import Any
#
# from django.contrib import admin
# from django.http import HttpRequest
#
#
# class ModelAdminPermissionsMixin:
#     can_read = True
#     can_create = True
#     can_update = True
#     can_delete = True
#     read_only = False
#
#     def has_delete_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
#         return self.can_delete and not self.read_only
#
#     def has_change_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
#         return self.can_update and not self.read_only
#
#     def has_add_permission(self, request: HttpRequest) -> bool:
#         return self.can_create and not self.read_only
#
#     def has_view_permission(self, request: HttpRequest, obj: Any | None = None) -> bool:
#         return self.can_read
#
#
# class BaseModelAdmin(ModelAdminPermissionsMixin, admin.ModelAdmin):
#     pass
