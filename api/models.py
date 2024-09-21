from django.db import models
from django.contrib.auth.hashers import make_password, check_password
import random
import string


class Teacher(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)  # Store encrypted
    role = models.CharField(max_length=10, default='teacher')

    def save(self, *args, **kwargs):
        if not self.pk:  # If this is a new teacher
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"Teacher: {self.name}"

class Student(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)  # Store encrypted
    role = models.CharField(max_length=10, default='student')

    def save(self, *args, **kwargs):
        if not self.pk:  # If this is a new student
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"Student: {self.name}"




class Class(models.Model):
    class_name = models.CharField(max_length=100)
    class_code = models.CharField(max_length=10, unique=True)  # Unique code to join the class
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)  # Relation to Teacher
    description = models.TextField(null=True, blank=True)
    students = models.ManyToManyField(Student, related_name='classes', blank=True)

    def save(self, *args, **kwargs):
        if not self.class_code:  # Generate a unique class code if it's not already set
            self.class_code = self.generate_unique_class_code()
        super().save(*args, **kwargs)

    def generate_unique_class_code(self):
        # Generate a random string of letters and digits
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        while Class.objects.filter(class_code=code).exists():  # Ensure the code is unique
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return code

    def __str__(self):
        return f"{self.class_name} by {self.teacher.name}"



from datetime import date

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_attended = models.ForeignKey(Class, on_delete=models.CASCADE)
    date = models.DateField(default=date.today)
    status = models.CharField(max_length=10, default='absent')  # Options: present/absent

    def __str__(self):
        return f"{self.student.name} - {self.class_attended.class_name} - {self.status}"
    



from django.utils import timezone
import uuid

class PasswordResetToken(models.Model):
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    def is_valid(self):
        return timezone.now() <= self.created_at + timezone.timedelta(hours=1)
