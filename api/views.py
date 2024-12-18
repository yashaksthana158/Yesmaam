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
from rest_framework.pagination import PageNumberPagination
from django.db.models import Max, Q
from openpyxl import Workbook


import qrcode
from io import BytesIO
from django.http import HttpResponse
from datetime import date
import pandas as pd
from reportlab.pdfgen import canvas


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
        print(request.session.keys())  # To see what session keys are available
        print(request.session.get('email'))  # To debug the email retrieval

        qr_data = request.data.get("qr_data")
        if 'email' not in request.session:
            return Response({"error": "Session email not found"}, status=status.HTTP_401_UNAUTHORIZED)

        
        # Assuming qr_data comes in format "class_id|date"
        try:
            class_code, scanned_date = qr_data.split('|')

            scanned_date = date.fromisoformat(scanned_date)

            current_class = Class.objects.get(class_code=class_code)
           
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
    



class AttendanceListView(APIView):
    def get(self, request, class_code):
        role = request.session.get('role')
        email = request.session.get('email')
        
        try:
            current_class = Class.objects.get(class_code=class_code)
            
            if role == 'student':
                # Get the student and their last 15 attendance entries
                student = Student.objects.get(email=email)
                attendance_records = Attendance.objects.filter(student=student, class_attended=current_class).order_by('-date')[:15]
                
                data = {
                    "class_name": current_class.class_name,
                    "attendance": [
                        {"date": record.date, "status": record.status}
                        for record in attendance_records
                    ]
                }
                return Response(data, status=status.HTTP_200_OK)
            
            elif role == 'teacher':
                today = date.today()
                
                # Fetch today's attendance first
                attendance_records = Attendance.objects.filter(class_attended=current_class, date=today)

                # If no attendance records are found for today, fetch the latest attendance entry
                if not attendance_records.exists():
                    attendance_records = Attendance.objects.filter(class_attended=current_class).order_by('-date')[:1]
                
                data = {
                    "class_name": current_class.class_name,
                    "attendance": [
                        {"student_name": record.student.name, "status": record.status}
                        for record in attendance_records
                    ] if attendance_records.exists() else []
                }
                return Response(data, status=status.HTTP_200_OK)
             
            else:
                return Response({"error": "Invalid role"}, status=status.HTTP_403_FORBIDDEN)
        
        except Class.DoesNotExist:
            return Response({"error": "Class not found"}, status=status.HTTP_404_NOT_FOUND)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)



""" 

class AttendanceListView(APIView):
    def get(self, request, class_code):
        role = request.session.get('role')
        email = request.session.get('email')

        # Optional date parameters for filtering by date or range
        specific_date = request.query_params.get('date')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        try:
            # Fetch class based on the provided class code
            current_class = Class.objects.get(class_code=class_code)

            # If the role is student, fetch attendance for that specific student
            if role == 'student':
                try:
                    student = Student.objects.get(email=email)
                except Student.DoesNotExist:
                    return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

                # Get attendance records for the student in the given class
                attendance_records = Attendance.objects.filter(
                    student=student, 
                    class_attended=current_class
                ).order_by('-date')

                data = {
                    "class_name": current_class.class_name,
                    "attendance": [
                        {"date": record.date, "status": record.status}
                        for record in attendance_records
                    ]
                }
                return Response(data, status=status.HTTP_200_OK)

            # If the role is teacher, fetch attendance for the entire class
            elif role == 'teacher':
                if specific_date:
                    attendance_records = Attendance.objects.filter(
                        class_attended=current_class, date=specific_date
                    ).order_by('date')
                elif start_date and end_date:
                    attendance_records = Attendance.objects.filter(
                        class_attended=current_class, 
                        date__range=[start_date, end_date]
                    ).order_by('date')
                else:
                    # Fetch today's attendance records by default
                    today = date.today()
                    attendance_records = Attendance.objects.filter(
                        class_attended=current_class, date=today
                    ).order_by('date')

                # Prepare the data to be returned
                data = {
                    "class_name": current_class.class_name,
                    "attendance": [
                        {"student_name": record.student.name, "status": record.status, "date": record.date}
                        for record in attendance_records
                    ]
                }
                return Response(data, status=status.HTTP_200_OK)

            else:
                return Response({"error": "Invalid role"}, status=status.HTTP_403_FORBIDDEN)

        except Class.DoesNotExist:
            return Response({"error": "Class not found"}, status=status.HTTP_404_NOT_FOUND)
        except Attendance.DoesNotExist:
            return Response({"error": "Attendance records not found"}, status=status.HTTP_404_NOT_FOUND) """



""" 
class ExportAttendanceView(APIView):
    def get(self, request, class_code, format_type):
        role = request.session.get('role')
        email = request.session.get('email')
        
        try:
            current_class = Class.objects.get(class_code=class_code)
            
            if role == 'student':
                student = Student.objects.get(email=email)
                attendance_records = Attendance.objects.filter(student=student, class_attended=current_class)
            elif role == 'teacher':
                attendance_records = Attendance.objects.filter(class_attended=current_class)
            else:
                return Response({"error": "Invalid role"}, status=status.HTTP_403_FORBIDDEN)
            
            # Prepare data for export
            attendance_data = [
                {"Student Name": record.student.name, "Date": record.date, "Status": record.status}
                for record in attendance_records
            ]

            if format_type == 'xlsx':
                return self.export_xlsx(attendance_data)
            elif format_type == 'pdf':
                return self.export_pdf(attendance_data)
            else:
                return Response({"error": "Invalid format"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Class.DoesNotExist:
            return Response({"error": "Class not found"}, status=status.HTTP_404_NOT_FOUND)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

    def export_xlsx(self, attendance_data):
        df = pd.DataFrame(attendance_data)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Attendance', index=False)
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=attendance.xlsx'
        return response

    def export_pdf(self, attendance_data):
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        p.drawString(100, 800, "Attendance Records")
        
        y_position = 750
        for record in attendance_data:
            p.drawString(100, y_position, f"Student Name: {record['Student Name']}, Date: {record['Date']}, Status: {record['Status']}")
            y_position -= 20
        
        p.showPage()
        p.save()
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=attendance.pdf'
        return response
 """



class TeacherFilterView(APIView):
    def get(self, request, class_code):
        role = request.session.get('role')

        # Optional date parameter for filtering by date
        specific_date = request.query_params.get('date')

        try:
            # Fetch class based on the provided class code
            current_class = Class.objects.get(class_code=class_code)

            # If the role is teacher, fetch attendance for the entire class
            if role == 'teacher':
                if specific_date:
                    attendance_records = Attendance.objects.filter(
                        class_attended=current_class, date=specific_date
                    ).order_by('date')
                else:
                    # Fetch today's attendance records by default
                    today = date.today()
                    attendance_records = Attendance.objects.filter(
                        class_attended=current_class, date=today
                    ).order_by('date')

                # Prepare the data to be returned
                data = {
                    "class_name": current_class.class_name,
                    "attendance": [
                        {"student_name": record.student.name, "status": record.status, "date": record.date}
                        for record in attendance_records
                    ]
                }
                return Response(data, status=status.HTTP_200_OK)

            else:
                return Response({"error": "Invalid role"}, status=status.HTTP_403_FORBIDDEN)

        except Class.DoesNotExist:
            return Response({"error": "Class not found"}, status=status.HTTP_404_NOT_FOUND)
        except Attendance.DoesNotExist:
            return Response({"error": "Attendance records not found"}, status=status.HTTP_404_NOT_FOUND)


class ExportAttendanceXLSX(APIView):
    def get(self, request, class_code):
        # Fetch attendance data
        attendance_records = Attendance.objects.filter(class_attended__class_code=class_code)
        
        wb = Workbook()
        ws = wb.active
        ws.append(['Student Name', 'Status', 'Date'])
        
        for record in attendance_records:
            ws.append([record.student.name, record.status, record.date.strftime('%Y-%m-%d')])
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=attendance_{class_code}.xlsx'
        wb.save(response)
        return response
    
class ExportAttendancePDF(APIView):
    def get(self, request, class_code):
        # Fetch attendance data
        attendance_records = Attendance.objects.filter(class_attended__class_code=class_code)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=attendance_{class_code}.pdf'
        
        p = canvas.Canvas(response)
        p.drawString(100, 800, f"Attendance for Class {class_code}")
        y = 750
        for record in attendance_records:
            p.drawString(100, y, f"Student: {record.student.name}, Status: {record.status}, Date: {record.date.strftime('%Y-%m-%d')}")
            y -= 20
        
        p.showPage()
        p.save()
        return response

class LogoutView(APIView):
    @csrf_exempt
    def post(self, request):
        logout(request)
        request.session.flush()  # Clear the session
        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)