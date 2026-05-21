from django.urls import include, path

from events.admin import uevent_admin_site
from events.views import home
from events.views import student_logout
from events.views import student_login
from events.views import verify_otp

urlpatterns = [
    path('', home, name='home'),
    path('api/', include('events.urls')),
    path('accounts/student-login/', student_login, name='student_login'),
    path('accounts/verify-otp/', verify_otp, name='verify_otp'),
    path('accounts/logout/', student_logout, name='student_logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', uevent_admin_site.urls),
]