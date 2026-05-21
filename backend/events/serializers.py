from rest_framework import serializers

from .models import Event, Registration, Student


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'


class RegistrationSerializer(serializers.ModelSerializer):
    student_number = serializers.CharField(source='student.student_number', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_date = serializers.DateField(source='event.date', read_only=True)
    event_location = serializers.CharField(source='event.location', read_only=True)

    class Meta:
        model = Registration
        fields = (
            'id',
            'student',
            'student_number',
            'student_email',
            'event',
            'event_title',
            'event_date',
            'event_location',
            'created_at',
        )