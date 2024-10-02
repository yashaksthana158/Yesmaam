"""
URL configuration for demo1backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from api import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', views.RegisterUser.as_view(), name='register'),
    path('login/',views.LoginView.as_view(), name='Login'),
    path('create_class/',views.CreateClassView.as_view(), name='create_class'),
    path('join_class/', views.JoinClassView.as_view(), name='join_class'),
    path('dashboard/<str:class_code>/', views.ClassDashboardView.as_view(), name='Class_dashboard'),
    path('mark_attendance/', views.MarkAttendanceView.as_view(), name='Mark_attendance'),
    path('generate_qr/<str:class_code>/', views.GenerateQRCodeView.as_view(), name='GenerateQrcode'),
    path('teacher/classes/', views.TeacherClassesView.as_view(), name='teacher-classes'),
    path('student/classes/', views.StudentClassesView.as_view(), name='student-classes'),
    path('password-reset-request/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/', views.PasswordResetView.as_view(), name='confirm_password'),
    path('class/<str:class_code>/people/', views.ClassPeopleView.as_view(), name='class_people_api'),
    path('logout/',views.LogoutView.as_view(), name='logout'),
]
