from django.contrib import admin

from .models import Event, Registration


class RegistrationInline(admin.TabularInline):
	model = Registration
	extra = 0
	fields = ('user', 'created_at')
	readonly_fields = ('created_at',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
	list_display = ('title', 'date', 'capacity', 'is_active', 'created_at')
	list_filter = ('is_active', 'date')
	search_fields = ('title', 'description')
	inlines = [RegistrationInline]


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
	list_display = ('user', 'event', 'created_at')
	list_filter = ('event', 'created_at')
	search_fields = ('user__username', 'event__title')
