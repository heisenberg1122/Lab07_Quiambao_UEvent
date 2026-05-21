from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.db import IntegrityError
from django.utils import timezone
from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import redirect, render
from rest_framework.permissions import AllowAny
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl, quote
import random
import logging
import re
from django.core.mail import send_mail

from .models import Event, Registration, Student
from .serializers import EventSerializer, RegistrationSerializer, StudentSerializer


User = get_user_model()
logger = logging.getLogger(__name__)

STUDENT_SESSION_KEYS = (
    'student_id',
    'student_number',
    'student_email',
    'auth_otp',
    'auth_student_number',
    'auth_student_email',
    'auth_next',
)


def get_current_student(request):
    student_id = request.session.get('student_id')
    if not student_id:
        return None

    try:
        return Student.objects.get(pk=student_id)
    except Student.DoesNotExist:
        for key in ('student_id', 'student_number', 'student_email'):
            request.session.pop(key, None)
        return None


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
    for key in STUDENT_SESSION_KEYS:
        request.session.pop(key, None)
    auth_logout(request)
    return redirect(next_url)


@api_view(['GET', 'POST'])
def events(request):
    if request.method == 'GET':
        events = Event.objects.filter(is_active=True).order_by('date', 'title')
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
@permission_classes([AllowAny])
def registrations(request):
    if request.method == 'GET':
        if request.user.is_staff:
            registrations_qs = Registration.objects.select_related('student', 'event').order_by('-created_at')
        else:
            student = get_current_student(request)
            if not student:
                return Response([])

            registrations_qs = Registration.objects.select_related('student', 'event').filter(student=student).order_by('-created_at')

        serializer = RegistrationSerializer(registrations_qs, many=True)
        return Response(serializer.data)

    student = get_current_student(request)
    if not student:
        return Response({'status': 'error', 'message': 'Student session not found.'}, status=401)

    event_id = request.data.get('event_id')
    if not event_id:
        return Response({'status': 'error', 'message': 'Missing event_id'}, status=400)

    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return Response({'status': 'error', 'message': 'Event not found'}, status=404)

    existing = Registration.objects.filter(student=student, event=event).first()
    if existing:
        return Response({'status': 'error', 'message': 'Already registered'}, status=400)

    if Registration.objects.filter(event=event).count() >= event.capacity:
        return Response({'status': 'error', 'message': 'Event is already full.'}, status=400)

    try:
        registration = Registration.objects.create(student=student, event=event)
    except IntegrityError:
        return Response({'status': 'error', 'message': 'Error in registration'}, status=500)

    return Response({'status': 'success', 'message': 'Registered successfully', 'registration': RegistrationSerializer(registration).data})

def registrations_resume(request):
    event_id = request.GET.get('event_id')
    redirect_to = request.GET.get('redirect') or '/'

    if not event_id:
        return redirect(redirect_to)

    try:
        event = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return redirect(redirect_to)

    student = get_current_student(request)
    if not student:
        return redirect(redirect_to)

    if not Registration.objects.filter(student=student, event=event).exists():
        if Registration.objects.filter(event=event).count() < event.capacity:
            try:
                Registration.objects.create(student=student, event=event)
            except IntegrityError:
                pass

    redirect_to = append_query_params(redirect_to, {
        'student_number': student.student_number,
        'student_email': student.email,
        'registered': event_id,
    })
    return redirect(redirect_to)


def student_login(request):
    next_url = request.GET.get('next') or 'http://localhost:5173/'
    action = request.GET.get('action') 
    student_number = request.GET.get('student_number', '').strip()
    student_email = request.GET.get('student_email', '').strip()
    
    login_page = "http://localhost:5173/login.html"

    if student_number and action:

        student_exists = Student.objects.filter(student_number=student_number).exists()
        legacy_user = User.objects.filter(username=student_number, is_staff=False).first()

        if action == 'register':
            if not student_email:
                return redirect(f"{login_page}?error={quote('Please enter your student email to create an account.')}")

            if not student_email.endswith('@ua.edu.ph'):
                return redirect(f"{login_page}?error={quote('Security Error: Only @ua.edu.ph emails are allowed.')}")

            if student_exists or legacy_user:
                return redirect(f"{login_page}?error={quote('This Student Number is already registered. Please use Sign In.')}")

            otp = str(random.randint(100000, 999999))
            
            request.session['auth_otp'] = otp
            request.session['auth_student_number'] = student_number
            request.session['auth_student_email'] = student_email
            request.session['auth_next'] = next_url

            send_mail(
                subject='UA Event Portal - Verification Code',
                message=f'Hello,\n\nYour verification code to create your UA Event account is: {otp}\n\nDo not share this code with anyone.',
                from_email='security@ua.edu.ph',
                recipient_list=[student_email],
                fail_silently=False,
            )

            return render(request, 'registration/verify_otp.html', {'email': student_email})

        elif action == 'login':
            if not student_exists and not legacy_user:
                return redirect(f"{login_page}?error={quote('Account not found. Please click Create Account.')}")

            if student_exists:
                student = Student.objects.get(student_number=student_number)
            else:
                student = Student.objects.create(
                    student_number=legacy_user.username,
                    email=legacy_user.email or f'{legacy_user.username}@ua.edu.ph',
                )
                legacy_user.delete()

            request.session['student_id'] = student.id
            request.session['student_number'] = student.student_number
            request.session['student_email'] = student.email
            
            redirect_url = append_query_params(next_url, {
                'student_number': student.student_number,
                'student_email': student.email,
            })
            return redirect(redirect_url)

    return HttpResponse("Invalid request parameters.", status=400)


def verify_otp(request):
    if request.method == 'POST':
        entered_otp = re.sub(r'\D', '', request.POST.get('otp', '').strip())
        stored_otp = re.sub(r'\D', '', str(request.session.get('auth_otp') or ''))

        if entered_otp and stored_otp and entered_otp == stored_otp:
            student_number = request.session.get('auth_student_number')
            student_email = request.session.get('auth_student_email')
            next_url = request.session.get('auth_next')

            try:
                student = Student.objects.get(student_number=student_number)
            except Student.DoesNotExist:
                student = Student.objects.create(student_number=student_number, email=student_email)

            request.session['student_id'] = student.id
            request.session['student_number'] = student.student_number
            request.session['student_email'] = student.email
            request.session.pop('auth_otp', None)
            request.session.pop('auth_student_number', None)
            request.session.pop('auth_student_email', None)
            request.session.pop('auth_next', None)

            redirect_url = append_query_params(next_url, {
                'student_number': student.student_number,
                'student_email': student.email,
            })
            return redirect(redirect_url)
        else:
            logger.warning(
                'OTP verification failed for email=%s student_number=%s entered=%s stored=%s',
                request.session.get('auth_student_email'),
                request.session.get('auth_student_number'),
                entered_otp,
                stored_otp,
            )
            return render(request, 'registration/verify_otp.html', {
                'email': request.session.get('auth_student_email'),
                'error': 'Invalid verification code. Please try again.'
            })
            
    return HttpResponse("Method not allowed", status=405)


@api_view(['GET'])
@permission_classes([AllowAny])
def auth_status(request):
    student = get_current_student(request)
    return Response({
        'authenticated': bool(student),
        'username': student.student_number if student else None,
        'email': student.email if student else None,
        'student': StudentSerializer(student).data if student else None,
    })