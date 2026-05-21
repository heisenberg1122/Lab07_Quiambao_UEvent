from django.urls import path
from .views import events, registrations, registrations_resume, auth_status

urlpatterns = [
    path('events/', events, name='events'),
    path('registrations/', registrations, name='registrations'),
    path('registrations/resume/', registrations_resume, name='registrations_resume'),
    path('auth-status/', auth_status, name='auth_status'),
]