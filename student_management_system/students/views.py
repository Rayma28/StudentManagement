from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Student, Result
from .forms import StudentForm, ResultForm
from datetime import datetime
from django.views.generic import CreateView
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Student, Fee
from django import forms

@login_required
def student_profile(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    
    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            student = form.save(commit=False)
            student.user = request.user
            student.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('student_profile')
    else:
        form = StudentForm(instance=student)
    
    return render(request, 'students/profile.html', {'form': form, 'student': student})

def calculate_grade(percentage):
    """Calculate letter grade based on percentage."""
    if percentage >= 90:
        return 'A+'
    elif percentage >= 80:
        return 'A'
    elif percentage >= 70:
        return 'B'
    elif percentage >= 60:
        return 'C'
    elif percentage >= 50:
        return 'D'
    else:
        return 'F'

@login_required
def student_results(request):
    """
    View to display paginated semester results for the current student.
    """
    student = get_object_or_404(Student, user=request.user)
    
    # Get all semester data using the model method
    semesters_data = student.get_all_semesters_data()
    
    # Convert to list of semesters sorted by semester number
    semesters_list = sorted(
        [{
            'semester': sem,
            **data,
            'results': student.get_semester_results(sem)
        } for sem, data in semesters_data.items()],
        key=lambda x: x['semester']
    )
    
    # Get requested page from query parameter
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1
    
    # Validate page number
    if page < 1 or page > len(semesters_list):
        page = 1
    
    # Get current semester data
    current_semester = semesters_list[page - 1] if semesters_list else None
    
    # Prepare pagination data
    if semesters_list:
        has_previous = page > 1
        has_next = page < len(semesters_list)
    else:
        has_previous = False
        has_next = False
    
    context = {
        'student': student,
        'current_semester': current_semester,
        'total_pages': len(semesters_list),
        'current_page': page,
        'has_previous': has_previous,
        'has_next': has_next,
        'has_results': len(semesters_list) > 0,
        'grade_scale': Student.GRADE_CHOICES if hasattr(Student, 'GRADE_CHOICES') else None
    }
    
    return render(request, 'students/results.html', context)

@login_required
class UploadResultView(CreateView):
    model = Result
    form_class = ResultForm
    template_name = 'students/upload_result.html'
    
    def form_valid(self, form):
        messages.success(self.request, 'Result uploaded successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_success_url(self):
        return '/upload-result/'

def upload_result(request):
    if request.method == 'POST':
        form = ResultForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Result uploaded successfully!')
            return redirect('upload_result')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ResultForm()
    
    return render(request, 'students/upload_result.html', {'form': form})

@login_required
def all_students(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view all students')
        return redirect('dashboard')
    
    # Get filter parameters from GET request
    name_filter = request.GET.get('name', '')
    enrollment_filter = request.GET.get('enrollment_id', '')
    email_filter = request.GET.get('email', '')
    page = request.GET.get('page', 1)
    
    # Start with all students
    students = Student.objects.all().order_by('enrollment_id')
    
    # Apply filters if provided
    if name_filter:
        students = students.filter(name__icontains=name_filter)
    if enrollment_filter:
        students = students.filter(enrollment_id__icontains=enrollment_filter)
    if email_filter:
        students = students.filter(email__icontains=email_filter)
    
    # Pagination - 10 students per page
    paginator = Paginator(students, 10)
    try:
        students_page = paginator.page(page)
    except PageNotAnInteger:
        students_page = paginator.page(1)
    except EmptyPage:
        students_page = paginator.page(paginator.num_pages)
    
    context = {
        'students': students_page,
        'name_filter': name_filter,
        'enrollment_filter': enrollment_filter,
        'email_filter': email_filter,
    }
    return render(request, 'students/all_students.html', context)

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
    grade = grade.strip()  # Remove any whitespace
    numeric_grade = GRADE_MAPPING.get(grade, 0.0)  # Default to 0.0 if grade not found
    if numeric_grade == 0.0 and grade:
        print(f"Warning: Grade '{grade}' not found in GRADE_MAPPING. Defaulting to 0.0.")
    return numeric_grade

@login_required
def student_detail(request, enrollment_id):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view student details')
        return redirect('dashboard')
    
    student = get_object_or_404(Student, enrollment_id=enrollment_id)
    results = Result.objects.filter(student=student).order_by('semester', 'exam_date')
    
    # Group results by semester
    semester_results = {}
    for result in results:
        semester = result.semester
        if semester not in semester_results:
            semester_results[semester] = []
        semester_results[semester].append(result)
    
    # Sort semesters to ensure consistent page-to-semester mapping
    sorted_semesters = sorted(semester_results.keys())
    
    # Get current page number from request
    page_number = request.GET.get('page', 1)
    
    # Map pages to semesters: page 1 = 1st semester, page 2 = 2nd semester, etc.
    paginator = Paginator(sorted_semesters, 1)  # 1 semester per page
    page_obj = paginator.get_page(page_number)
    
    # Get the current semester for this page
    current_semester = None
    current_semester_results = []
    chart_labels = []  # Subjects for the x-axis
    chart_grades = []  # Numeric grades for the y-axis
    if page_obj.object_list:
        current_semester = page_obj.object_list[0]  # First (and only) semester on this page
        current_semester_results = semester_results.get(current_semester, [])
        # Prepare chart data
        chart_labels = [result.subject for result in current_semester_results]
        chart_grades = [convert_grade_to_numeric(result.grade) for result in current_semester_results]
        # Debug: Log the chart data
        print(f"Semester: {current_semester}")
        print(f"Chart Labels: {chart_labels}")
        print(f"Chart Grades: {chart_grades}")
    
    context = {
        'student': student,
        'current_semester': current_semester,
        'current_semester_results': current_semester_results,
        'paginator': paginator,
        'page_obj': page_obj,
        'chart_labels': json.dumps(chart_labels),  # Safe for JavaScript
        'chart_grades': json.dumps(chart_grades),
    }
    return render(request, 'students/student_detail.html', context)

# Fee Form for Add/Update
class FeeForm(forms.ModelForm):
    class Meta:
        model = Fee
        fields = ['semester', 'amount', 'due_date', 'is_paid', 'payment_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }

# Fee Form for Add/Update
class FeeForm(forms.ModelForm):
    class Meta:
        model = Fee
        fields = ['semester', 'amount', 'due_date', 'is_paid', 'payment_date']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_paid = cleaned_data.get('is_paid')
        payment_date = cleaned_data.get('payment_date')

        # Validation: If is_paid is False, payment_date should be None
        if not is_paid and payment_date:
            self.add_error('payment_date', 'Payment date should be empty if the fee is not paid.')
        # Optional: If is_paid is True, ensure payment_date is set
        if is_paid and not payment_date:
            self.add_error('payment_date', 'Please specify the payment date since the fee is marked as paid.')

        return cleaned_data

@login_required
def fees_view(request):
    # Check if user has a student profile
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    
    fee_records = []
    students = []
    show_all_fees = request.user.is_staff
    selected_student_id = request.GET.get('student_id', '')
    
    if show_all_fees:
        all_fees = Fee.objects.all().order_by('student__enrollment_id', 'semester')
        if selected_student_id:
            try:
                selected_student_id_int = int(selected_student_id)
                all_fees = all_fees.filter(student__id=selected_student_id_int)
            except (ValueError, TypeError):
                selected_student_id = ''
        for fee in all_fees:
            fee_data = {
                'id': fee.id,
                'student_name': fee.student.name,
                'enrollment_id': fee.student.enrollment_id,
                'semester': fee.semester,
                'amount': str(fee.amount),
                'due_date': fee.due_date.strftime('%Y-%m-%d'),
                'is_paid': fee.is_paid,
                'payment_date': fee.payment_date.strftime('%Y-%m-%d') if fee.payment_date else 'N/A',
            }
            fee_records.append(fee_data)
        students = Student.objects.all()
    elif student:
        fees = Fee.objects.filter(student=student).order_by('semester')
        for fee in fees:
            fee_data = {
                'id': fee.id,
                'semester': fee.semester,
                'amount': str(fee.amount),
                'due_date': fee.due_date.strftime('%Y-%m-%d'),
                'is_paid': fee.is_paid,
                'payment_date': fee.payment_date.strftime('%Y-%m-%d') if fee.payment_date else 'N/A',
            }
            fee_records.append(fee_data)
    
    context = {
        'student': student,
        'fee_records': fee_records,
        'user': request.user,
        'show_all_fees': show_all_fees,
        'students': students,
        'selected_student_id': selected_student_id,
    }
    return render(request, 'students/fees.html', context)

@login_required
def add_fee(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to add fee records.')
        return redirect('fees')
    
    if request.method == 'POST':
        form = FeeForm(request.POST)
        if form.is_valid():
            student_id = request.POST.get('student_id')
            student = get_object_or_404(Student, id=student_id)
            fee = form.save(commit=False)
            fee.student = student
            # Ensure is_paid is correctly set
            fee.is_paid = form.cleaned_data['is_paid']
            # If not paid, ensure payment_date is None
            if not fee.is_paid:
                fee.payment_date = None
            fee.save()
            messages.success(request, 'Fee record added successfully.')
            return redirect('fees')
    else:
        form = FeeForm()
    
    students = Student.objects.all()
    context = {
        'form': form,
        'students': students,
    }
    return render(request, 'students/add_fee.html', context)

@login_required
def update_fee(request, fee_id):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to update fee records.')
        return redirect('fees')
    
    fee = get_object_or_404(Fee, id=fee_id)
    if request.method == 'POST':
        form = FeeForm(request.POST, instance=fee)
        if form.is_valid():
            fee = form.save(commit=False)
            # Ensure is_paid is correctly set
            fee.is_paid = form.cleaned_data['is_paid']
            # If not paid, ensure payment_date is None
            if not fee.is_paid:
                fee.payment_date = None
            fee.save()
            messages.success(request, 'Fee record updated successfully.')
            return redirect('fees')
    else:
        form = FeeForm(instance=fee)
    
    context = {
        'form': form,
        'fee': fee,
    }
    return render(request, 'students/update_fee.html', context)