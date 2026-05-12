"""
URL configuration for uevent project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import include, path

from events.admin import uevent_admin_site
from events.views import home
from events.views import student_logout
from events.views import student_login

urlpatterns = [
    path('', home),
    path('api/', include('events.urls')),
    path('accounts/student-login/', student_login, name='student_login'),
    path('accounts/logout/', student_logout, name='student_logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', uevent_admin_site.urls),
]
