from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Student, Result, FeeRecord, Department, Course, Semester, Subject, Enrollment
from .forms import StudentForm, ResultForm
from datetime import datetime
from django.views.generic import CreateView
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django import forms
from django.contrib.auth.decorators import user_passes_test
from .forms import DepartmentForm, CourseForm, SemesterForm, SubjectForm, EnrollmentForm

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

@login_required
class UploadResultView(CreateView):
    model = Result
    form_class = ResultForm
    template_name = 'students/upload_result.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not self.request.user.is_staff:
            student = get_object_or_404(Student, user=self.request.user)
            kwargs['student'] = student
        return kwargs
    
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
        student = None if request.user.is_staff else get_object_or_404(Student, user=request.user)
        form = ResultForm(request.POST, request.FILES, student=student)
        if form.is_valid():
            result = form.save()
            messages.success(request, 'Result uploaded successfully!')
            return redirect('upload_result')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        student = None if request.user.is_staff else get_object_or_404(Student, user=request.user)
        form = ResultForm(student=student)
    
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
    results = Result.objects.filter(student=student).order_by('semester__semester_number', 'exam_date')
    
    # Get enrollment details
    enrollment = student.enrollments.first()
    department_name = enrollment.department.name if enrollment else 'Not enrolled'
    course_name = enrollment.course.name if enrollment else 'Not enrolled'
    
    # Group results by semester
    semester_results = {}
    for result in results:
        semester_num = str(result.semester.semester_number)
        if semester_num not in semester_results:
            semester_results[semester_num] = []
        semester_results[semester_num].append(result)
    
    # Sort semesters to ensure consistent page-to-semester mapping
    sorted_semesters = sorted(semester_results.keys(), key=int)
    
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
        chart_labels = [result.subject.name for result in current_semester_results]
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
        'department_name': department_name,
        'course_name': course_name,
    }
    return render(request, 'students/student_detail.html', context)

@login_required
def update_fee(request, fee_id):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to update fee records.')
        return redirect('fees')
    
    fee = get_object_or_404(Fee, id=fee_id)
    if request.method == 'POST':
        form = FeeForm(request.POST, instance=fee, student=fee.student)
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
        form = FeeForm(instance=fee, student=fee.student)
    
    context = {
        'form': form,
        'fee': fee,
    }
    return render(request, 'students/update_fee.html', context)

# Check if user is staff
def is_staff(user):
    return user.is_authenticated and user.is_staff

@user_passes_test(is_staff)
def department_view(request):
    # Fetch all records from the database
    departments = Department.objects.all()
    courses = Course.objects.all()
    semesters = Semester.objects.all()
    subjects = Subject.objects.all()
    enrollments = Enrollment.objects.all()
    students = Student.objects.all()

    # Initialize forms
    dept_form = DepartmentForm()
    course_form = CourseForm()
    semester_form = SemesterForm()
    subject_form = SubjectForm()
    enroll_form = EnrollmentForm()

    if request.method == 'POST':
        # Handle Department form submission
        if 'dept_submit' in request.POST:
            dept_form = DepartmentForm(request.POST)
            if dept_form.is_valid():
                dept_form.save()
                messages.success(request, 'Department added successfully!')
                return redirect('department')
            else:
                messages.error(request, 'Error adding department. Check your input.')

        # Handle Course form submission
        elif 'course_submit' in request.POST:
            course_form = CourseForm(request.POST)
            if course_form.is_valid():
                course_form.save()
                messages.success(request, 'Course added successfully!')
                return redirect('department')
            else:
                messages.error(request, 'Error adding course. Check your input.')

        # Handle Semester form submission
        elif 'semester_submit' in request.POST:
            semester_form = SemesterForm(request.POST)
            if semester_form.is_valid():
                semester_form.save()
                messages.success(request, 'Semester added successfully!')
                return redirect('department')
            else:
                messages.error(request, 'Error adding semester. Check your input.')

        # Handle Subject form submission
        elif 'subject_submit' in request.POST:
            subject_form = SubjectForm(request.POST)
            if subject_form.is_valid():
                subject_form.save()
                messages.success(request, 'Subject added successfully!')
                return redirect('department')
            else:
                messages.error(request, 'Error adding subject. Check your input.')

        # Handle Enrollment form submission
        elif 'enroll_submit' in request.POST:
            enroll_form = EnrollmentForm(request.POST)
            if enroll_form.is_valid():
                enroll_form.save()
                messages.success(request, 'Enrollment added successfully!')
                return redirect('department')
            else:
                messages.error(request, 'Error adding enrollment. Check your input.')

    context = {
        'dept_form': dept_form,
        'course_form': course_form,
        'semester_form': semester_form,
        'subject_form': subject_form,
        'enroll_form': enroll_form,
        'departments': departments,
        'courses': courses,
        'semesters': semesters,
        'subjects': subjects,
        'enrollments': enrollments,
        'students': students,
    }
    return render(request, 'students/department.html', context)

@login_required
def student_results(request):
    # Fetch all students and semesters for staff filtering
    students = Student.objects.all()
    semesters = Semester.objects.all()
    
    # Initialize variables
    results = Result.objects.none()
    current_semester = None
    student_selected = False
    page_obj = None
    
    if request.user.is_staff:
        # Staff: Filter by student and/or semester
        student_id = request.GET.get('student')
        semester_id = request.GET.get('semester')
        
        if student_id:
            try:
                selected_student = Student.objects.get(id=student_id)
                student_selected = True
                # Get semesters for the student's enrolled course
                enrollment = selected_student.enrollments.first()
                if enrollment:
                    student_semesters = Semester.objects.filter(course=enrollment.course).order_by('semester_number')
                    # Get results for the selected student
                    results = Result.objects.filter(student=selected_student).order_by('semester__semester_number', 'subject__name')
                else:
                    results = Result.objects.none()
                    messages.error(request, 'Selected student has no enrollment.')
            except Student.DoesNotExist:
                results = Result.objects.none()
                messages.error(request, 'Selected student does not exist.')
        elif semester_id:
            # Filter by semester only
            try:
                results = Result.objects.filter(semester_id=semester_id).order_by('semester__semester_number', 'subject__name')
                current_semester = Semester.objects.get(id=semester_id)
            except Semester.DoesNotExist:
                results = Result.objects.none()
                messages.error(request, 'Selected semester does not exist.')
        else:
            # No filters: Show all results (no pagination)
            results = Result.objects.all().order_by('semester__semester_number', 'subject__name')
    else:
        # Student: Show only their results
        try:
            student = Student.objects.get(user=request.user)
            enrollment = student.enrollments.first()
            if enrollment:
                student_semesters = Semester.objects.filter(course=enrollment.course).order_by('semester_number')
                results = Result.objects.filter(student=student).order_by('semester__semester_number', 'subject__name')
            else:
                results = Result.objects.none()
                messages.error(request, 'No enrollment found. Please contact the administrator.')
        except Student.DoesNotExist:
            results = Result.objects.none()
            messages.error(request, 'No student profile found. Please contact the administrator.')

    # Apply pagination if a student is selected (staff) or for a student user
    if student_selected or not request.user.is_staff:
        if 'student_semesters' in locals():
            # Create a paginator based on semesters
            paginator = Paginator(student_semesters, 1)  # 1 semester per page
            page_number = request.GET.get('page', 1)
            try:
                page_obj = paginator.page(page_number)
                # Get the semester for the current page
                current_semester = page_obj.object_list.first()
                if current_semester:
                    # Filter results to only the current semester
                    results = results.filter(semester=current_semester)
                else:
                    results = Result.objects.none()
            except (PageNotAnInteger, EmptyPage):
                # Default to first page or empty
                page_obj = paginator.page(1)
                current_semester = page_obj.object_list.first()
                if current_semester:
                    results = results.filter(semester=current_semester)
                else:
                    results = Result.objects.none()

    context = {
        'results': results,
        'students': students,
        'semesters': semesters,
        'current_semester': current_semester,
        'student_selected': student_selected,
        'page_obj': page_obj,
    }
    return render(request, 'students/student_results.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import FeeRecord, Student
from .forms import FeeRecordForm

def is_staff(user):
    return user.is_staff

@login_required
def my_fees(request):
    if request.user.is_staff:
        fee_records = FeeRecord.objects.all().order_by('-payment_date')
    else:
        student = get_object_or_404(Student, user=request.user)
        fee_records = FeeRecord.objects.filter(student=student).order_by('-payment_date')
    
    context = {
        'fee_records': fee_records,
        'is_staff': request.user.is_staff,
    }
    return render(request, 'students/my_fees.html', context)

@login_required
@user_passes_test(is_staff)
def add_fee_record(request):
    if request.method == 'POST':
        form = FeeRecordForm(request.POST, user=request.user)
        if form.is_valid():
            fee_record = form.save(commit=False)
            fee_record.created_by = request.user
            fee_record.save()
            messages.success(request, 'Fee record added successfully!')
            return redirect('my_fees')
    else:
        form = FeeRecordForm(user=request.user)
    
    context = {'form': form}
    return render(request, 'students/fee_form.html', context)

@login_required
@user_passes_test(is_staff)
def edit_fee_record(request, pk):
    fee_record = get_object_or_404(FeeRecord, pk=pk)
    if request.method == 'POST':
        form = FeeRecordForm(request.POST, instance=fee_record, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fee record updated successfully!')
            return redirect('my_fees')
    else:
        form = FeeRecordForm(instance=fee_record, user=request.user)
    
    context = {'form': form, 'edit_mode': True}
    return render(request, 'students/fee_form.html', context)

@login_required
@user_passes_test(is_staff)
def delete_fee_record(request, pk):
    fee_record = get_object_or_404(FeeRecord, pk=pk)
    if request.method == 'POST':
        fee_record.delete()
        messages.success(request, 'Fee record deleted successfully!')
        return redirect('my_fees')
    
    context = {'fee_record': fee_record}
    return render(request, 'students/confirm_delete_fee.html', context)