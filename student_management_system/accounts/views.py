from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from students.models import Student
from django.templatetags.static import static
from django.db.models import Q
from datetime import datetime
from students.models import Student, Result
from django.contrib.auth.decorators import login_required
from django.utils import timezone
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
    # Define default images for different user types
    default_images = {
        'default': static('images/default_user.png'),
        'student': static('images/student.png'),
        'teacher': static('images/teacher.png'),
        'admin': static('images/admin.png')
    }
    
    # Initialize with default image
    login_image = default_images['default']
    
    # Check if user is already authenticated (might happen if they revisit login page)
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

# Grade to numeric value conversion (using midpoint of typical grade ranges)
GRADE_MAPPING = {
    'A+': 95,  # Outstanding, midpoint of 90-100
    'A': 85,   # Excellent, midpoint of 80-89
    'B+': 75,  # Very Good, midpoint of 70-79
    'B': 65,   # Good, midpoint of 60-69
    'C+': 55,  # Average, midpoint of 50-59
    'C': 45,   # Below Average, midpoint of 40-49
    'F': 20,   # Fail, midpoint of 0-40
}

def convert_grade_to_numeric(grade):
    """Convert a letter grade to a numeric value for charting."""
    return GRADE_MAPPING.get(grade, 0.0)  # Default to 0.0 if grade not found

@login_required
def dashboard_view(request):
    # Get student profile if exists
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    
    # Get statistics data (for staff only)
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
    
    # Initialize variables for student progress graphs
    all_semester_labels = []
    all_semester_averages = []
    
    # Get fee-related data for all users
    fee_data = {}
    if student:
        # All Semesters Progress: Get average grade per semester
        all_semesters = Result.objects.filter(student=student).values('semester').distinct().order_by('semester')
        for semester in all_semesters:
            semester_name = semester['semester']
            semester_results = Result.objects.filter(student=student, semester=semester_name)
            if semester_results.exists():
                avg_grade = sum(convert_grade_to_numeric(r.grade) for r in semester_results) / semester_results.count()
                all_semester_labels.append(semester_name)
                all_semester_averages.append(round(avg_grade, 2))
        
        # Fee data: Using the Fee model with amount, is_paid, and due_date
        try:
            latest_fee = student.fees.order_by('-due_date').first()  # Using related_name='fees'
            if latest_fee:
                fee_data = {
                    'amount': latest_fee.amount,
                    'is_paid': latest_fee.is_paid,
                    'status': 'Paid' if latest_fee.is_paid else 'Pending',
                    'due_date': latest_fee.due_date.strftime('%Y-%m-%d') if latest_fee.due_date else 'N/A',
                    'payment_date': latest_fee.payment_date.strftime('%Y-%m-%d') if latest_fee.payment_date else 'N/A',
                    'semester': latest_fee.semester,
                }
            else:
                fee_data = {
                    'amount': 0,
                    'is_paid': False,
                    'status': 'No fees recorded',
                    'due_date': 'N/A',
                    'payment_date': 'N/A',
                    'semester': 'N/A',
                }
        except AttributeError:
            # Handle case where Fee model or relationship is misconfigured
            fee_data = {
                'amount': 0,
                'is_paid': False,
                'status': 'Fee data unavailable',
                'due_date': 'N/A',
                'payment_date': 'N/A',
                'semester': 'N/A',
            }
    
    # Context for template
    context = {
        'student': student,
        'total_students': total_students,
        'active_students': active_students,
        'new_this_year': new_this_year,
        'total_results': total_results,
        'all_semester_labels': json.dumps(all_semester_labels),
        'all_semester_averages': json.dumps(all_semester_averages),
        'fee_data': fee_data,
    }
    return render(request, 'accounts/dashboard.html', context)

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        # Check if the email exists in your database (example)
        # You might need to adjust this based on your User model
        from django.contrib.auth.models import User
        if User.objects.filter(email=email).exists():
            # Send email
            subject = "Password Reset Link"
            message = "Click this link to reset your password: http://your-website.com/reset-password/"
            from_email = "youruniversity.sms@gmail.com"
            recipient_list = [email]
            
            send_mail(subject, message, from_email, recipient_list)
            
            messages.success(request, "Password reset link sent to your email!")
            return redirect('login')  # Redirect to login page
        else:
            messages.error(request, "Email not found!")
    
    return render(request, 'forgot_password.html')