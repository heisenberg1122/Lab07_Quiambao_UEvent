from django.conf import settings
from django.db import models


class Event(models.Model):
	title = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	location = models.CharField(max_length=255, blank=True, default='')
	date = models.DateField()
	capacity = models.PositiveIntegerField()
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['date', 'title']

	def __str__(self):
		return self.title

	@property
	def registered_count(self):
		return self.registrations.count()

	@property
	def remaining_slots(self):
		return max(self.capacity - self.registered_count, 0)


class Registration(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_registrations')
	event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['user', 'event'], name='unique_user_event_registration'),
		]

	def __str__(self):
		return f'{self.user} -> {self.event}'
