from django.urls import path

from .views import events, registrations, registrations_resume
from .views import auth_status


urlpatterns = [
    path('events/', events),
    path('registrations/', registrations),
    path('registrations/resume/', registrations_resume),
    path('auth-status/', auth_status),
]