from rest_framework import serializers
from .models import Teacher, Student,Class

class TeacherRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = ['name', 'email', 'password']

    def create(self, validated_data):
        teacher = Teacher.objects.create(
            name=validated_data['name'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return teacher

class StudentRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['name', 'email', 'password']

    def create(self, validated_data):
        student = Student.objects.create(
            name=validated_data['name'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return student
    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=128)



class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, min_length=8)




class ClassSerializer(serializers.ModelSerializer):
    class_code = serializers.ReadOnlyField()  # Generated automatically, so read-only

    class Meta:
        model = Class
        fields = ['id','class_name', 'class_code', 'description']  # 'teacher' is excluded

    def create(self, validated_data):
        return Class.objects.create(**validated_data)


