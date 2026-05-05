from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Event, Registration
from .serializers import EventSerializer, RegistrationSerializer


User = get_user_model()


def home(request):
    return HttpResponse(
        '<h1>U-Event Backend</h1>'
        '<p>API endpoints:</p>'
        '<ul>'
        '<li><a href="/api/events/">/api/events/</a></li>'
        '<li><a href="/api/registrations/">/api/registrations/</a></li>'
        '</ul>'
    )


@api_view(['GET', 'POST'])
def events(request):
    if request.method == 'GET':
        events = Event.objects.filter(is_active=True, date__gte=timezone.localdate()).order_by('date', 'title')
        data = []

        for event in events:
            serializer = EventSerializer(event)
            item = serializer.data
            registered_count = Registration.objects.filter(event=event).count()
            item['registered_count'] = registered_count
            item['remaining_slots'] = max(event.capacity - registered_count, 0)
            data.append(item)

        return Response(data)

    title = request.data.get('title')
    description = request.data.get('description', '')
    date = request.data.get('date')
    capacity = request.data.get('capacity')

    if not title or not date or not capacity:
        return Response({
            'status': 'error',
            'message': 'Missing required event data'
        })

    event = Event.objects.create(
        title=title,
        description=description,
        date=date,
        capacity=capacity,
    )
    return Response(EventSerializer(event).data)


@api_view(['GET', 'POST'])
def registrations(request):
    if request.method == 'GET':
        registrations = Registration.objects.select_related('user', 'event').order_by('-created_at')
        serializer = RegistrationSerializer(registrations, many=True)
        return Response(serializer.data)

    user_id = request.data.get('user_id')
    event_id = request.data.get('event_id')

    if not user_id or not event_id:
        return Response({
            'status': 'error',
            'message': 'Missing user_id or event_id'
        })

    try:
        user, _ = User.objects.get_or_create(username=str(user_id))
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response({
            'status': 'error',
            'message': 'Event not found'
        })

    existing = Registration.objects.filter(user=user, event=event).first()
    if existing:
        return Response({
            'status': 'error',
            'message': 'Already registered'
        })

    if Registration.objects.filter(event=event).count() >= event.capacity:
        return Response({
            'status': 'error',
            'message': 'Event is already full.'
        })

    try:
        registration = Registration.objects.create(user=user, event=event)
    except IntegrityError:
        return Response({
            'status': 'error',
            'message': 'Error in registration'
        })

    return Response({
        'status': 'success',
        'message': 'Registered successfully',
        'registration': RegistrationSerializer(registration).data,
    })
