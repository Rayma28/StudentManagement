from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Student, Department, Course, Enrollment, Semester, Subject, Result
from django.core.exceptions import ValidationError

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['enrollment_id', 'name', 'email', 'address', 'phone', 'date_of_birth', 'photo']
        widgets = {
            'enrollment_id': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['student', 'semester', 'subject', 'marks', 'total_marks', 'grade', 'exam_date', 'result_file']
        widgets = {
            'student': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Student'
            }),
            'semester': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_semester'
            }),
            'subject': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_subject',
                'placeholder': 'Subject will be populated based on semester'
            }),
            'marks': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter marks obtained',
                'min': '0',
                'max': '100'
            }),
            'total_marks': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter total marks',
                'min': '1',
                'max': '100'
            }),
            'grade': forms.Select(attrs={
                'class': 'form-select',
                'readonly': 'readonly'
            }),
            'exam_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'result_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            })
        }
    
    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        if student:
            self.fields['student'].widget = forms.HiddenInput()
            self.fields['student'].initial = student
            self.fields['student'].queryset = Student.objects.filter(id=student.id)
            enrollment = student.enrollments.first()
            if enrollment:
                self.fields['semester'].queryset = Semester.objects.filter(course=enrollment.course) if enrollment.course else Semester.objects.none()
            else:
                self.fields['semester'].queryset = Semester.objects.none()
        else:
            self.fields['student'].queryset = Student.objects.all()
            self.fields['student'].empty_label = "Select Student"

        if 'semester' in self.data:
            try:
                semester_id = int(self.data.get('semester'))
                self.fields['subject'].queryset = Subject.objects.filter(semester__id=semester_id)
            except (ValueError, TypeError):
                self.fields['subject'].queryset = Subject.objects.none()
        elif self.instance and hasattr(self.instance, "semester") and self.instance.semester_id:
            self.fields['subject'].queryset = Subject.objects.filter(semester=self.instance.semester)
        else:
            self.fields['subject'].queryset = Subject.objects.none()

        self.fields['grade'].widget.attrs['readonly'] = True

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        empty_label="Select Department",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    enrollment_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'department', 'enrollment_date']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            student = Student.objects.create(
                user=user,
                enrollment_id=f"S{user.id:04d}",
                name=user.username,
                email=user.email,
                address="",
                phone="",
                date_of_birth="2000-01-01"
            )
            Enrollment.objects.create(
                student=student,
                department=self.cleaned_data['department'],
                enrollment_date=self.cleaned_data['enrollment_date']
            )
        return user

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Computer Science'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Department description'}),
        }

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['department', 'name', 'duration_years', 'total_semesters']
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., B.Tech'}),
            'duration_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'total_semesters': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semester
        fields = ['course', 'semester_number']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-select'}),
            'semester_number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['semester', 'name', 'code', 'credits']
        widgets = {
            'semester': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Data Structures'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CS101'}),
            'credits': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['student', 'department', 'course', 'enrollment_date', 'is_active']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'enrollment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
from django import forms
from .models import FeeRecord, Student

class FeeRecordForm(forms.ModelForm):
    class Meta:
        model = FeeRecord
        fields = ['student', 'amount', 'payment_date', 'due_date', 
                 'payment_method', 'status', 'description']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(FeeRecordForm, self).__init__(*args, **kwargs)
        
        if user and not user.is_staff:
            self.fields['student'].queryset = Student.objects.filter(user=user)
            self.fields['student'].disabled = True