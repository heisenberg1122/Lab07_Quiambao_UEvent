from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.db import IntegrityError
from django.utils import timezone
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import redirect
from django.shortcuts import render
from rest_framework.permissions import AllowAny
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from .models import Event, Registration
from .serializers import EventSerializer, RegistrationSerializer


User = get_user_model()


def append_query_params(url, params):
    """Return `url` with the provided query params merged in."""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({key: value for key, value in params.items() if value is not None and value != ''})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def home(request):
    return HttpResponse(
        '<h1>U-Event Backend</h1>'
        '<p>API endpoints:</p>'
        '<ul>'
        '<li><a href="/api/events/">/api/events/</a></li>'
        '<li><a href="/api/registrations/">/api/registrations/</a></li>'
        '</ul>'
    )


def student_logout(request):
    next_url = request.GET.get('next') or 'http://localhost:5173/'
    auth_logout(request)
    return redirect(next_url)


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
    location = request.data.get('location', '')
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
        location=location,
        date=date,
        capacity=capacity,
    )
    return Response(EventSerializer(event).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def registrations(request):
    """List or create registrations for authenticated users.

    - GET: if staff, return all registrations; otherwise return only the current user's registrations.
    - POST: create a registration for the authenticated user for the given `event_id`.
    """
    if request.method == 'GET':
        if request.user.is_staff:
            registrations_qs = Registration.objects.select_related('user', 'event').order_by('-created_at')
        else:
            registrations_qs = Registration.objects.select_related('user', 'event').filter(user=request.user).order_by('-created_at')

        serializer = RegistrationSerializer(registrations_qs, many=True)
        return Response(serializer.data)

    # POST
    event_id = request.data.get('event_id')
    if not event_id:
        return Response({'status': 'error', 'message': 'Missing event_id'}, status=400)

    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response({'status': 'error', 'message': 'Event not found'}, status=404)

    existing = Registration.objects.filter(user=request.user, event=event).first()
    if existing:
        return Response({'status': 'error', 'message': 'Already registered'}, status=400)

    if Registration.objects.filter(event=event).count() >= event.capacity:
        return Response({'status': 'error', 'message': 'Event is already full.'}, status=400)

    try:
        registration = Registration.objects.create(user=request.user, event=event)
    except IntegrityError:
        return Response({'status': 'error', 'message': 'Error in registration'}, status=500)

    return Response({'status': 'success', 'message': 'Registered successfully', 'registration': RegistrationSerializer(registration).data})


@login_required
def registrations_resume(request):
    """Resume registration flow after login.

    This endpoint is intended to be used as the `next` target for the login flow.
    It accepts `event_id` and an optional `redirect` param (frontend URL to return to).
    It creates the registration for the logged-in user and then redirects to `redirect` if provided,
    otherwise to the site root.
    """
    event_id = request.GET.get('event_id')
    redirect_to = request.GET.get('redirect') or '/'

    if not event_id:
        return redirect(redirect_to)

    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return redirect(redirect_to)

    # create registration if not exists and if capacity allows
    if not Registration.objects.filter(user=request.user, event=event).exists():
        if Registration.objects.filter(event=event).count() < event.capacity:
            try:
                Registration.objects.create(user=request.user, event=event)
            except IntegrityError:
                pass

    redirect_to = append_query_params(redirect_to, {
        'student_number': request.user.username,
        'student_email': request.user.email,
        'registered': event_id,
    })
    return redirect(redirect_to)


def student_login(request):
    """Simple student login / account creation.

    - If the student number exists, log the user in and refresh the stored email
      with the submitted email when needed.
    - If the student number does not exist, create the account using the submitted email.
    - The view accepts a `next` parameter to redirect after login.
    """
    next_url = request.GET.get('next') or request.POST.get('next') or 'http://localhost:5173/'
    student_number = ''
    student_email = ''

    if request.method == 'POST':
        student_number = request.POST.get('student_number', '').strip()
        student_email = request.POST.get('student_email', '').strip()
    elif request.method == 'GET':
        student_number = request.GET.get('student_number', '').strip()
        student_email = request.GET.get('student_email', '').strip()

    # If we have both student_number and student_email, attempt login/create flow.
    if student_number or student_email:
        if not student_number or not student_email:
            return render(request, 'registration/student_login.html', {
                'next': next_url,
                'error': 'Please provide both student number and student email.'
            })

        try:
            validate_email(student_email)
        except ValidationError:
            return render(request, 'registration/student_login.html', {
                'next': next_url,
                'error': 'Please provide a valid email address.'
            })

        try:
            user = User.objects.get(username=str(student_number))
            if (user.email or '').lower() != student_email.lower():
                user.email = student_email
                user.save(update_fields=['email'])

            if not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active'])

        except User.DoesNotExist:
            user = User.objects.create(username=str(student_number), email=student_email, is_active=True)

        auth_login(request, user)
        redirect_url = append_query_params(next_url, {
            'student_number': user.username,
            'student_email': user.email,
        })
        return redirect(redirect_url)

    return render(request, 'registration/student_login.html', {'next': next_url})


@api_view(['GET'])
@permission_classes([AllowAny])
def auth_status(request):
    """Return basic authentication status for the current session."""
    user = request.user
    return Response({
        'authenticated': bool(user and user.is_authenticated),
        'username': user.username if user and user.is_authenticated else None,
        'email': user.email if user and user.is_authenticated else None,
    })
