from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, Q, Sum
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.html import format_html

from .models import Event, Registration, Student


class UEventAdminSite(admin.AdminSite):
	site_header = 'UA Event Admin'
	site_title = 'UA Event Control Panel'
	index_title = 'Events and Registrations'
	index_template = 'admin/uevent_index.html'
	site_url = '/'

	def index(self, request, extra_context=None):
		today = timezone.localdate()
		event_stats = Event.objects.aggregate(
			total_events=Count('id'),
			open_events=Count('id', filter=Q(is_active=True)),
			upcoming_events=Count('id', filter=Q(date__gte=today)),
			total_capacity=Sum('capacity'),
		)
		registration_stats = Registration.objects.aggregate(total_registrations=Count('id'))
		recent_events = Event.objects.order_by('-created_at')[:5]
		recent_registrations = Registration.objects.select_related('student', 'event').order_by('-created_at')[:5]

		stats = {
			'total_events': event_stats['total_events'] or 0,
			'open_events': event_stats['open_events'] or 0,
			'upcoming_events': event_stats['upcoming_events'] or 0,
			'total_capacity': event_stats['total_capacity'] or 0,
			'total_registrations': registration_stats['total_registrations'] or 0,
			'total_slots_left': sum(event.remaining_slots for event in Event.objects.all()),
		}

		context = {
			**self.each_context(request),
			'title': self.index_title,
			'app_list': self.get_app_list(request),
			'event_stats': stats,
			'recent_events': recent_events,
			'recent_registrations': recent_registrations,
		}
		if extra_context:
			context.update(extra_context)
		return TemplateResponse(request, self.index_template, context)


uevent_admin_site = UEventAdminSite(name='uevent_admin')


@admin.action(description='Mark selected events as active')
def activate_events(modeladmin, request, queryset):
	queryset.update(is_active=True)


@admin.action(description='Mark selected events as inactive')
def deactivate_events(modeladmin, request, queryset):
	queryset.update(is_active=False)


class RegistrationInline(admin.TabularInline):
	model = Registration
	extra = 0
	fields = ('student', 'created_at')
	readonly_fields = ('created_at',)
	can_delete = False


@admin.register(Event, site=uevent_admin_site)
class EventAdmin(admin.ModelAdmin):
	list_display = ('title', 'date', 'location', 'capacity', 'is_active', 'registered_total', 'remaining_total', 'status_badge', 'created_at')
	list_filter = ('is_active', 'date')
	search_fields = ('title', 'description', 'location')
	list_editable = ('capacity', 'is_active')
	date_hierarchy = 'date'
	ordering = ('date', 'title')
	actions = [activate_events, deactivate_events]
	readonly_fields = ('created_at', 'registered_total', 'remaining_total')
	fieldsets = (
		('Event Information', {
			'fields': ('title', 'description', 'location', 'date')
		}),
		('Capacity and Status', {
			'fields': ('capacity', 'is_active')
		}),
		('System Info', {
			'fields': ('created_at', 'registered_total', 'remaining_total')
		}),
	)
	inlines = [RegistrationInline]
	save_on_top = True

	@admin.display(description='Registered')
	def registered_total(self, obj):
		return obj.registered_count

	@admin.display(ordering='capacity', description='Remaining')
	def remaining_total(self, obj):
		return obj.remaining_slots

	@admin.display(description='Status')
	def status_badge(self, obj):
		if obj.is_active:
			return format_html('<span style="color:#166534;font-weight:700;">Open</span>')
		return format_html('<span style="color:#991b1b;font-weight:700;">Closed</span>')


@admin.register(Registration, site=uevent_admin_site)
class RegistrationAdmin(admin.ModelAdmin):
	list_display = ('student', 'event', 'event_date', 'created_at')
	list_filter = ('event', 'created_at')
	search_fields = ('student__student_number', 'student__email', 'event__title', 'event__location')
	autocomplete_fields = ('event',)
	list_select_related = ('student', 'event')
	ordering = ('-created_at',)
	readonly_fields = ('created_at',)
	fieldsets = (
		('Registration Details', {
			'fields': ('student', 'event')
		}),
		('System Info', {
			'fields': ('created_at',)
		}),
	)

	@admin.display(ordering='event__date', description='Event Date')
	def event_date(self, obj):
		return obj.event.date


@admin.register(Student, site=uevent_admin_site)
class StudentAdmin(admin.ModelAdmin):
	list_display = ('student_number', 'email', 'created_at')
	search_fields = ('student_number', 'email')
	ordering = ('student_number',)
	readonly_fields = ('created_at',)
	fieldsets = (
		('Student Account', {
			'fields': ('student_number', 'email')
		}),
		('System Info', {
			'fields': ('created_at',)
		}),
	)


uevent_admin_site.register(Group, GroupAdmin)
uevent_admin_site.register(get_user_model(), UserAdmin)
