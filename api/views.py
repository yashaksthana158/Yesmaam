from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from .models import Teacher, Student,Class,Attendance,PasswordResetToken
from .serializers import TeacherRegistrationSerializer, StudentRegistrationSerializer,LoginSerializer,ClassSerializer,PasswordResetRequestSerializer,PasswordResetSerializer
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Q  # Import Q for complex queries
from django.contrib.auth import login, authenticate,logout
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404

import qrcode
from io import BytesIO
from django.http import HttpResponse
from datetime import date


class RegisterUser(APIView):
    
    def post(self, request):
        role = request.data.get('role')  # Retrieve the selected role from the request

        if role not in ['teacher', 'student']:
            return Response({"error": "Invalid role selected"}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the email from the request
        email = request.data.get('email')

        # Check if email already exists in either Teacher or Student model
        if Teacher.objects.filter(email=email).exists() or Student.objects.filter(email=email).exists():
            return Response({"error": "This email is already used by another account"}, status=status.HTTP_400_BAD_REQUEST)

        # Handle registration based on the role
        try:
            if role == 'teacher':
                serializer = TeacherRegistrationSerializer(data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return Response({"message": "Teacher registered successfully"}, status=status.HTTP_201_CREATED)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            elif role == 'student':
                serializer = StudentRegistrationSerializer(data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return Response({"message": "Student registered successfully"}, status=status.HTTP_201_CREATED)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except IntegrityError:
            return Response({"error": "User with this email already exists"}, status=status.HTTP_400_BAD_REQUEST)




class LoginView(APIView):
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            # Check if user is a teacher
            try:
                teacher = Teacher.objects.get(email=email)
                if check_password(password, teacher.password):
                    # Store the user's email and role in the session
                    request.session['email'] = teacher.email
                    request.session['role'] = 'teacher'

                    return Response({'role': 'teacher'}, status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
            except Teacher.DoesNotExist:
                pass

            # Check if user is a student
            try:
                student = Student.objects.get(email=email)
                if check_password(password, student.password):
                    # Store the user's email and role in the session
                    request.session['email'] = student.email
                    request.session['role'] = 'student'
                    return Response({'role': 'student'}, status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
            except Student.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    




class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            # Check if email exists
            user_exists = Teacher.objects.filter(email=email).exists() or Student.objects.filter(email=email).exists()
            if user_exists:
                token = PasswordResetToken.objects.create(email=email)
                # Send token to user's email (simplified)
                send_mail(
                    'Password Reset',
                    f'Use this token to reset your password: {token.token}',
                    'noreply@example.com',
                    [email]
                )
                return Response({'message': 'Password reset token sent to email'}, status=status.HTTP_200_OK)
            return Response({'error': 'Email not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            token_value = serializer.validated_data['token']
            password = serializer.validated_data['password']

            try:
                reset_token = PasswordResetToken.objects.get(token=token_value)
                if not reset_token.is_valid():
                    return Response({'error': 'Token expired'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Update the user's password
                if Teacher.objects.filter(email=reset_token.email).exists():
                    teacher = Teacher.objects.get(email=reset_token.email)
                    teacher.password = make_password(password)
                    teacher.save()
                elif Student.objects.filter(email=reset_token.email).exists():
                    student = Student.objects.get(email=reset_token.email)
                    student.password = make_password(password)
                    student.save()

                reset_token.delete()  # Token used, so delete it
                return Response({'message': 'Password reset successful'}, status=status.HTTP_200_OK)

            except PasswordResetToken.DoesNotExist:
                return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CreateClassView(APIView):

    @csrf_exempt
    def post(self, request):
        # Retrieve the role and email from the session
        user_role = request.session.get('role')
        teacher_email = request.session.get('email')

        if not teacher_email or user_role != 'teacher':
            return Response({"error": "Permission denied: Only teachers can create classes."},
                            status=status.HTTP_403_FORBIDDEN)

        # Find the teacher object using the email from the session
        try:
            teacher = Teacher.objects.get(email=teacher_email)
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher not found"}, status=status.HTTP_404_NOT_FOUND)

        # Pass the class data to the serializer and assign the teacher
        serializer = ClassSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(teacher=teacher)  # Automatically assign the teacher
            print(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    
class JoinClassView(APIView):

    @csrf_exempt
    def post(self, request):
        student_email = request.session.get('email')
        class_code = request.data.get('class_code')

        if not student_email:
            return Response({'error': 'Student not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

        # Get the student object
        try:
            student = Student.objects.get(email=student_email)
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get the class by class_code
        try:
            class_obj = Class.objects.get(class_code=class_code)
        except Class.DoesNotExist:
            return Response({'error': 'Class not found'}, status=status.HTTP_404_NOT_FOUND)

        # Add the student to the class
        class_obj.students.add(student)
        return Response({'message': 'Joined class successfully','class_code':class_code}, status=status.HTTP_200_OK)





    



class GenerateQRCodeView(APIView):
    def get(self, request, class_code):
        try:
            current_class = Class.objects.get(class_code=class_code)
            
            # Data to be encoded in QR (class_id|date)
            qr_data = f"{current_class.class_code}|{str(date.today())}"
            qr = qrcode.make(qr_data)
            buffer = BytesIO()
            qr.save(buffer)
            buffer.seek(0)
            
            # Returning the QR code as a PNG image
            return HttpResponse(buffer, content_type="image/png")
        except Class.DoesNotExist:
            return Response({"error": "Class not found"}, status=status.HTTP_404_NOT_FOUND)




class MarkAttendanceView(APIView):
    @csrf_exempt
    def post(self, request):
        qr_data = request.data.get("qr_data")
        
        # Assuming qr_data comes in format "class_id|date"
        try:
            class_code, scanned_date = qr_data.split('|')
            current_class = Class.objects.get(class_code=class_code)
            print(request.data)
            student = Student.objects.get(email=request.session['email'])
            
            # Mark attendance for the student on the given date
            attendance, created = Attendance.objects.get_or_create(
                student=student, class_attended=current_class, date=scanned_date
            )
            if created:
                attendance.status = 'present'
                attendance.save()
                return Response({"message": "Attendance marked successfully"}, status=status.HTTP_200_OK)
            return Response({"error": "Attendance already marked"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Class.DoesNotExist:
            return Response({"error": "Class not found"}, status=status.HTTP_404_NOT_FOUND)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({"error": "Invalid QR data"}, status=status.HTTP_400_BAD_REQUEST)
        

class ClassDashboardView(APIView):
    def get(self, request, class_code):
        role = request.session.get('role')  # Assuming role is stored in the session
        
        try:
            current_class = Class.objects.get(class_code=class_code)
            
            if role == 'teacher':
                # Teacher's View: List of students and their attendance status
                attendance_records = Attendance.objects.filter(class_attended=current_class)
                data = {
                    "class_name": current_class.class_name,
                    "students_attendance": [
                        {"student_name": record.student.name, "status": record.status, "date": record.date}
                        for record in attendance_records
                    ]
                }
                return Response(data, status=status.HTTP_200_OK)
            
            elif role == 'student':
                # Student's View: Only their own attendance records
                student = Student.objects.get(email=request.session['email'])
                attendance_records = Attendance.objects.filter(student=student, class_attended=current_class)
                data = {
                    "class_name": current_class.class_name,
                    "attendance": [
                        {"status": record.status, "date": record.date}
                        for record in attendance_records
                    ]
                }
                return Response(data, status=status.HTTP_200_OK)
            
            else:
                return Response({"error": "Invalid role"}, status=status.HTTP_403_FORBIDDEN)
        
        except Class.DoesNotExist:
            return Response({"error": "Class not found"}, status=status.HTTP_404_NOT_FOUND)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

#All the classes a teacher has created
class TeacherClassesView(APIView):
    @csrf_exempt
    def get(self, request):
        teacher_email = request.session.get('email')
        if not teacher_email or request.session.get('role') != 'teacher':
            return Response({"error": "Permission denied: Only teachers can access this."}, 
                            status=status.HTTP_403_FORBIDDEN)

        try:
            teacher = Teacher.objects.get(email=teacher_email)
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher not found"}, status=status.HTTP_404_NOT_FOUND)

        classes = Class.objects.filter(teacher=teacher)
        class_data = [{"class_name": c.class_name, "class_code": c.class_code} for c in classes]

        return Response({"classes": class_data}, status=status.HTTP_200_OK)
    
""" class ClassPeopleView(APIView):
    def get(self, request, class_code):
        # Retrieve the class by class_code
        class_obj = get_object_or_404(Class, class_code=class_code)
        
        # Prepare the response data
        data = {
            'class_name': class_obj.class_name,
            'teacher': {
                'name': class_obj.teacher.name,
                'email': class_obj.teacher.email,
            },
            'students': [
                {
                    'name': student.name,
                    'email': student.email,
                } for student in class_obj.students.all()
            ]
        }
        
        return Response(data, status=status.HTTP_200_OK) """

class ClassPeopleView(APIView):
    def get(self, request, class_code):
        class_obj = get_object_or_404(Class, class_code=class_code)
        
        # Prepare response in the format expected by the Flutter frontend
        people = []
        
        # Add teacher as the first person in the list
        people.append({
            'name': class_obj.teacher.name,
            'role': 'Teacher',
        })
        
        # Add students to the list
        for student in class_obj.students.all():
            people.append({
                'name': student.name,
                'role': 'Student',
            })

        data = {
            'people': people
        }
        
        return Response(data, status=status.HTTP_200_OK)

    
#All the classes a student has join 
class StudentClassesView(APIView):
    @csrf_exempt
    def get(self, request):
        student_email = request.session.get('email')
        if not student_email or request.session.get('role') != 'student':
            return Response({"error": "Permission denied: Only students can access this."}, 
                            status=status.HTTP_403_FORBIDDEN)

        try:
            student = Student.objects.get(email=student_email)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        classes = student.classes.all()
        class_data = [{"class_name": c.class_name, "class_code": c.class_code} for c in classes]

        return Response({"classes": class_data}, status=status.HTTP_200_OK)



class LogoutView(APIView):
    @csrf_exempt
    def post(self, request):
        logout(request)
        request.session.flush()  # Clear the session
        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)