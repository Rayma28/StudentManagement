# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from students.models import Student, Result, Attendance, Enrollment, Semester
from django.templatetags.static import static
from django.db.models import Q
from datetime import datetime
import json
from django.core.mail import send_mail
from students.forms import RegistrationForm

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    default_images = {
        'default': static('images/default_user.png'),
        'student': static('images/student.png'),
        'teacher': static('images/teacher.png'),
        'admin': static('images/admin.png')
    }
    login_image = default_images['default']
    if request.user.is_authenticated:
        try:
            profile = request.user.userprofile
            if request.user.is_superuser:
                login_image = default_images['admin']
            elif request.user.is_staff:
                login_image = default_images['teacher']
            else:
                login_image = default_images['student']
        except UserProfile.DoesNotExist:
            login_image = default_images['student']
    
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'accounts/login.html', {'login_image': login_image})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('login')

GRADE_MAPPING = {
    'A+': 95,
    'A': 85,
    'B+': 75,
    'B': 65,
    'C+': 55,
    'C': 45,
    'F': 20,
}

def convert_grade_to_numeric(grade):
    return GRADE_MAPPING.get(grade.strip(), 0.0)

@login_required
def dashboard_view(request):
    student = None
    current_semester = None
    all_semester_labels = []
    all_semester_averages = []
    
    try:
        student = Student.objects.get(user=request.user)
        enrollment = student.enrollments.filter(is_active=True).first()
        if enrollment and enrollment.course:
            current_semester = Semester.objects.filter(course=enrollment.course).order_by('-semester_number').first()
    except Student.DoesNotExist:
        messages.error(request, 'No student profile found. Please complete your profile.')
    
    total_students = 0
    active_students = 0
    new_this_year = 0
    total_results = 0
    if request.user.is_staff:
        students = Student.objects.all()
        total_students = students.count()
        active_students = students.filter(is_active=True).count()
        current_year = datetime.now().year
        new_this_year = students.filter(created_at__year=current_year).count()
        total_results = Result.objects.count()
    
    fee_data = {}
    if student and not request.user.is_staff:
        all_semesters = Result.objects.filter(student=student).values('semester').distinct().order_by('semester')
        for semester in all_semesters:
            semester_id = semester['semester']
            semester_obj = Semester.objects.get(id=semester_id)
            semester_results = Result.objects.filter(student=student, semester=semester_id)
            if semester_results.exists():
                avg_grade = sum(convert_grade_to_numeric(r.grade) for r in semester_results) / semester_results.count()
                all_semester_labels.append(f"Semester {semester_obj.semester_number}")
                all_semester_averages.append(round(avg_grade, 2))
        
        try:
            latest_fee = student.fee_records.order_by('-due_date').first()
            if latest_fee:
                fee_data = {
                    'amount': latest_fee.amount,
                    'status': latest_fee.status,
                    'due_date': latest_fee.due_date.strftime('%Y-%m-%d') if latest_fee.due_date else 'N/A',
                    'payment_date': latest_fee.payment_date.strftime('%Y-%m-%d') if latest_fee.payment_date else 'N/A',
                    'semester': latest_fee.student.get_current_semester() or 'N/A',
                }
            else:
                fee_data = {
                    'amount': 0,
                    'status': 'No fees recorded',
                    'due_date': 'N/A',
                    'payment_date': 'N/A',
                    'semester': 'N/A',
                }
        except AttributeError:
            fee_data = {
                'amount': 0,
                'status': 'Fee data unavailable',
                'due_date': 'N/A',
                'payment_date': 'N/A',
                'semester': 'N/A',
            }
    
    context = {
        'student': student,
        'total_students': total_students,
        'active_students': active_students,
        'new_this_year': new_this_year,
        'total_results': total_results,
        'all_semester_labels': json.dumps(all_semester_labels),
        'all_semester_averages': json.dumps(all_semester_averages),
        'fee_data': fee_data,
        'current_semester': current_semester,
    }
    return render(request, 'accounts/dashboard.html', context)

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if User.objects.filter(email=email).exists():
            subject = "Password Reset Link"
            message = "Click this link to reset your password: http://your-website.com/reset-password/"
            from_email = "youruniversity.sms@gmail.com"
            recipient_list = [email]
            send_mail(subject, message, from_email, recipient_list)
            messages.success(request, "Password reset link sent to your email!")
            return redirect('login')
        else:
            messages.error(request, "Email not found!")
    
    return render(request, 'accounts/forgot_password.html')