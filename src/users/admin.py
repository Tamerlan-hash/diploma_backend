from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from .models import UserProfile

# Define an inline admin descriptor for UserProfile model
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'profile'
    fk_name = 'user'

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_car_number', 'get_car_model', 'get_avatar')
    readonly_fields = ('get_avatar',)

    def get_car_number(self, obj):
        return obj.profile.car_number if hasattr(obj, 'profile') else ''
    get_car_number.short_description = 'Car Number'

    def get_car_model(self, obj):
        return obj.profile.car_model if hasattr(obj, 'profile') else ''
    get_car_model.short_description = 'Car Model'

    def get_avatar(self, obj):
        if hasattr(obj, 'profile') and obj.profile.avatar:
            return mark_safe(f'<img src="{obj.profile.avatar.url}" width="50" height="50" />')
        return 'No Avatar'
    get_avatar.short_description = 'Avatar'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
