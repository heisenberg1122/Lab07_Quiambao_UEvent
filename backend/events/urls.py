from django.urls import path

from .views import events, registrations


urlpatterns = [
    path('events/', events),
    path('registrations/', registrations),
]