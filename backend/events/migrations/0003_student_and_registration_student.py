from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def forwards(apps, schema_editor):
    Student = apps.get_model('events', 'Student')
    Registration = apps.get_model('events', 'Registration')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))

    legacy_users = User.objects.filter(is_staff=False).order_by('id')
    for user in legacy_users:
        student_email = user.email or f'{user.username}@ua.edu.ph'
        student, _ = Student.objects.get_or_create(
            student_number=user.username,
            defaults={'email': student_email},
        )
        if student.email != student_email:
            student.email = student_email
            student.save(update_fields=['email'])

        Registration.objects.filter(user=user, student__isnull=True).update(student=student)

    legacy_users.delete()


def backwards(apps, schema_editor):
    # This migration is intentionally one-way for the current app flow.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0002_event_location'),
    ]

    operations = [
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student_number', models.CharField(max_length=50, unique=True)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['student_number'],
            },
        ),
        migrations.AddField(
            model_name='registration',
            name='student',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='event_registrations', to='events.student'),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveConstraint(
            model_name='registration',
            name='unique_user_event_registration',
        ),
        migrations.RemoveField(
            model_name='registration',
            name='user',
        ),
        migrations.AlterField(
            model_name='registration',
            name='student',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='event_registrations', to='events.student'),
        ),
        migrations.AddConstraint(
            model_name='registration',
            constraint=models.UniqueConstraint(fields=('student', 'event'), name='unique_student_event_registration'),
        ),
    ]
