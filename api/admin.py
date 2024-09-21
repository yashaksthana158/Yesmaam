from django.contrib import admin
from .models import Teacher, Student,Class,Attendance

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'password', 'role']

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'password', 'role']
@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ('id','class_name', 'class_code', 'description')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
     list_display = ('student', 'class_attended', 'date', 'status')

