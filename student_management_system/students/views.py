from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_GET
from .models import Student, Result, FeeRecord, Department, Course, Semester, Subject, Enrollment, Attendance, Lecture
from .forms import StudentForm, ResultForm, DepartmentForm, CourseForm, SemesterForm, SubjectForm, EnrollmentForm, FeeRecordForm, AttendanceFilterForm, AttendanceFormSet, LectureForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
import logging
from datetime import datetime
from django.forms import formset_factory
from django.db.models import F

logger = logging.getLogger(__name__)

def is_staff(user):
    return user.is_authenticated and user.is_staff

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
def upload_result(request):
    student = None if request.user.is_staff else get_object_or_404(Student, user=request.user)
    
    if request.method == 'POST':
        form = ResultForm(request.POST, request.FILES, student=student)
        if form.is_valid():
            result = form.save()
            messages.success(request, 'Result uploaded successfully!')
            return redirect('upload_result')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ResultForm(student=student)
    
    return render(request, 'students/upload_result.html', {'form': form})

@login_required
def get_subjects(request):
    semester_id = request.GET.get('semester_id')
    logger.debug(f"Request URL: {request.get_full_path()}, Semester ID: {semester_id}")
    
    if not semester_id:
        return JsonResponse({'error': 'semester_id is required'}, status=400)
    
    try:
        subjects = Subject.objects.filter(semester_id=semester_id).values('id', 'name')
        return JsonResponse({'subjects': list(subjects)})
    except Exception as e:
        logger.error(f"Error fetching subjects: {str(e)}")
        return JsonResponse({'error': 'An error occurred while fetching subjects'}, status=500)

from .models import (
    Subject, Student, Semester, Attendance, FeeRecord, Department, Course,
    Enrollment, Result, Lecture
)
from .forms import (
    FeeRecordForm, DepartmentForm, CourseForm, SemesterForm, SubjectForm,
    EnrollmentForm, AttendanceForm, AttendanceFilterForm, LectureForm
)

logger = logging.getLogger(__name__)

def is_staff(user):
    return user.is_staff

@require_GET
@login_required
def get_subjects(request):
    semester_id = request.GET.get('semester_id')
    if semester_id:
        try:
            subjects = Subject.objects.filter(semester__id=semester_id).values('id', 'name')
            return JsonResponse({'subjects': list(subjects)})
        except ValueError:
            return JsonResponse({'subjects': []}, status=400)
    return JsonResponse({'subjects': []}, status=400)

@login_required
def all_students(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view all students')
        return redirect('dashboard')
    
    name_filter = request.GET.get('name', '')
    enrollment_filter = request.GET.get('enrollment_id', '')
    email_filter = request.GET.get('email', '')
    page = request.GET.get('page', 1)
    
    students = Student.objects.all().order_by('enrollment_id')
    
    if name_filter:
        students = students.filter(name__icontains=name_filter)
    if enrollment_filter:
        students = students.filter(enrollment_id__icontains=enrollment_filter)
    if email_filter:
        students = students.filter(email__icontains=email_filter)
    
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

@login_required
@user_passes_test(is_staff)
def student_attendance(request, enrollment_id):
    try:
        student = Student.objects.get(enrollment_id=enrollment_id)
        semester_attendance = []
        student_semesters = Semester.objects.none()

        enrollments = student.enrollments.all()
        if enrollments.exists():
            student_semesters = Semester.objects.filter(
                course__in=[enrollment.course for enrollment in enrollments]
            ).order_by('semester_number').distinct()

            for semester in student_semesters:
                subjects = Subject.objects.filter(
                    attendances__student=student,
                    semester=semester
                ).distinct()
                
                if subjects.exists():
                    attendance_records = Attendance.objects.filter(
                        student=student,
                        subject__semester=semester
                    )
                    total_classes = attendance_records.count()
                    present_classes = attendance_records.filter(status='P').count()
                    percentage = round((present_classes / total_classes) * 100, 2) if total_classes > 0 else 0.0
                    
                    subject_summary = []
                    for subject in subjects:
                        subject_records = Attendance.objects.filter(
                            student=student,
                            subject=subject,
                            subject__semester=semester
                        )
                        subject_total = subject_records.count()
                        subject_present = subject_records.filter(status='P').count()
                        subject_absent = subject_total - subject_present
                        subject_percentage = round((subject_present / subject_total) * 100, 2) if subject_total > 0 else 0.0
                        
                        subject_summary.append({
                            'subject': subject,
                            'total_classes': subject_total,
                            'present_classes': subject_present,
                            'absent_classes': subject_absent,
                            'percentage': subject_percentage,
                        })
                    
                    semester_attendance.append({
                        'semester': semester,
                        'total_classes': total_classes,
                        'present_classes': present_classes,
                        'percentage': percentage,
                        'subject_summary': subject_summary,
                    })
        
        paginator = Paginator(semester_attendance, 1)
        page = request.GET.get('page')
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        context = {
            'semester_attendance': page_obj,
            'student': student,
            'student_semesters': student_semesters,
        }
        return render(request, 'students/student_attendance.html', context)
    except Student.DoesNotExist:
        messages.error(request, 'Student not found.')
        return redirect('all_students')

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
    grade = grade.strip()
    numeric_grade = GRADE_MAPPING.get(grade, 0.0)
    if numeric_grade == 0.0 and grade:
        logger.warning(f"Grade '{grade}' not found in GRADE_MAPPING. Defaulting to 0.0.")
    return numeric_grade

@login_required
def student_detail(request, enrollment_id):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view student details')
        return redirect('dashboard')
    
    student = get_object_or_404(Student, enrollment_id=enrollment_id)
    results = Result.objects.filter(student=student).order_by('semester__semester_number', 'exam_date')
    
    enrollment = student.enrollments.first()
    if enrollment:
        department_name = enrollment.department.name if enrollment.department else 'Not enrolled'
        course_name = enrollment.course.name if enrollment.course else 'Not enrolled'
    else:
        department_name = 'Not enrolled'
        course_name = 'Not enrolled'
    
    semester_results = {}
    for result in results:
        semester_num = str(result.semester.semester_number)
        if semester_num not in semester_results:
            semester_results[semester_num] = []
        semester_results[semester_num].append(result)
    
    sorted_semesters = sorted(semester_results.keys(), key=int)
    
    page_number = request.GET.get('page', 1)
    
    paginator = Paginator(sorted_semesters, 1)
    page_obj = paginator.get_page(page_number)
    
    current_semester = None
    current_semester_results = []
    chart_labels = []
    chart_grades = []
    if page_obj.object_list:
        current_semester = page_obj.object_list[0]
        current_semester_results = semester_results.get(current_semester, [])
        chart_labels = [result.subject.name for result in current_semester_results]
        chart_grades = [convert_grade_to_numeric(result.grade) for result in current_semester_results]
    
    context = {
        'student': student,
        'current_semester': current_semester,
        'current_semester_results': current_semester_results,
        'paginator': paginator,
        'page_obj': page_obj,
        'chart_labels': json.dumps(chart_labels),
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
    
    fee = get_object_or_404(FeeRecord, id=fee_id)
    if request.method == 'POST':
        form = FeeRecordForm(request.POST, instance=fee, user=fee.student)
        if form.is_valid():
            fee = form.save(commit=False)
            fee.is_paid = form.cleaned_data['is_paid']
            if not fee.is_paid:
                fee.payment_date = None
            fee.save()
            messages.success(request, 'Fee record updated successfully.')
            return redirect('my_fees')
    else:
        form = FeeRecordForm(instance=fee, user=fee.student)
    
    context = {
        'form': form,
        'fee': fee,
    }
    return render(request, 'students/update_fee.html', context)

@user_passes_test(is_staff)
def department_view(request):
    departments = Department.objects.all()
    dept_form = DepartmentForm()
    
    if request.method == 'POST':
        if 'dept_submit' in request.POST:
            dept_form = DepartmentForm(request.POST)
            if dept_form.is_valid():
                dept_form.save()
                messages.success(request, 'Department added successfully!')
                return redirect('departments')
            else:
                messages.error(request, 'Error adding department. Check your input.')
    
    paginator = Paginator(departments, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'dept_form': dept_form,
        'departments': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'students/departments.html', context)

@user_passes_test(is_staff)
def delete_department(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    department.delete()
    messages.success(request, 'Department deleted successfully!')
    return redirect('departments')

@user_passes_test(is_staff)
def course_view(request):
    courses = Course.objects.all()
    course_form = CourseForm()
    
    if request.method == 'POST':
        if 'course_submit' in request.POST:
            course_form = CourseForm(request.POST)
            if course_form.is_valid():
                course_form.save()
                messages.success(request, 'Course added successfully!')
                return redirect('courses')
            else:
                messages.error(request, 'Error adding course. Check your input.')
    
    paginator = Paginator(courses, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'course_form': course_form,
        'courses': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'students/courses.html', context)

@user_passes_test(is_staff)
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    course.delete()
    messages.success(request, 'Course deleted successfully!')
    return redirect('courses')

@user_passes_test(is_staff)
def semester_view(request):
    semesters = Semester.objects.all()
    semester_form = SemesterForm()
    
    if request.method == 'POST':
        if 'semester_submit' in request.POST:
            semester_form = SemesterForm(request.POST)
            if semester_form.is_valid():
                semester_form.save()
                messages.success(request, 'Semester added successfully!')
                return redirect('semesters')
            else:
                messages.error(request, 'Error adding semester. Check your input.')
    
    paginator = Paginator(semesters, 5)
    page_number = request.GET.get(' attenuates')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'semester_form': semester_form,
        'semesters': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'students/semesters.html', context)

@user_passes_test(is_staff)
def delete_semester(request, semester_id):
    semester = get_object_or_404(Semester, id=semester_id)
    semester.delete()
    messages.success(request, 'Semester deleted successfully!')
    return redirect('semesters')

@user_passes_test(is_staff)
def subject_view(request):
    subjects = Subject.objects.all()
    subject_form = SubjectForm()
    
    if request.method == 'POST':
        if 'subject_submit' in request.POST:
            subject_form = SubjectForm(request.POST)
            if subject_form.is_valid():
                subject_form.save()
                messages.success(request, 'Subject added successfully!')
                return redirect('subjects')
            else:
                messages.error(request, 'Error adding subject. Check your input.')
    
    paginator = Paginator(subjects, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'subject_form': subject_form,
        'subjects': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'students/subjects.html', context)

@user_passes_test(is_staff)
def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    subject.delete()
    messages.success(request, 'Subject deleted successfully!')
    return redirect('subjects')

@user_passes_test(is_staff)
def enrollment_view(request):
    enrollments = Enrollment.objects.all()
    enroll_form = EnrollmentForm()
    
    if request.method == 'POST':
        if 'enroll_submit' in request.POST:
            enroll_form = EnrollmentForm(request.POST)
            if enroll_form.is_valid():
                enroll_form.save()
                messages.success(request, 'Enrollment added successfully!')
                return redirect('enrollments')
            else:
                messages.error(request, 'Error adding enrollment. Check your input.')
    
    paginator = Paginator(enrollments, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'enroll_form': enroll_form,
        'enrollments': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'students/enrollments.html', context)

@user_passes_test(is_staff)
def delete_enrollment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    enrollment.delete()
    messages.success(request, 'Enrollment deleted successfully!')
    return redirect('enrollments')

@login_required
def student_results(request):
    students = Student.objects.all()
    semesters = Semester.objects.all()
    
    results = Result.objects.none()
    student_selected = False
    page_obj = None
    
    if request.user.is_staff:
        student_id = request.GET.get('student')
        semester_id = request.GET.get('semester')
        
        if student_id and semester_id:
            try:
                selected_student = Student.objects.get(id=student_id)
                selected_semester = Semester.objects.get(id=semester_id)
                student_selected = True
                results = Result.objects.filter(student=selected_student, semester=selected_semester).order_by('subject__name')
            except Student.DoesNotExist:
                results = Result.objects.none()
                messages.error(request, 'Selected student does not exist.')
            except Semester.DoesNotExist:
                results = Result.objects.none()
                messages.error(request, 'Selected semester does not exist.')
        elif student_id:
            try:
                selected_student = Student.objects.get(id=student_id)
                student_selected = True
                enrollment = selected_student.enrollments.first()
                if enrollment:
                    results = Result.objects.filter(student=selected_student).order_by('semester__semester_number', 'subject__name')
                else:
                    results = Result.objects.none()
                    messages.error(request, 'Selected student has no enrollment.')
            except Student.DoesNotExist:
                results = Result.objects.none()
                messages.error(request, 'Selected student does not exist.')
        elif semester_id:
            try:
                selected_semester = Semester.objects.get(id=semester_id)
                results = Result.objects.filter(semester=selected_semester).order_by('student__name', 'subject__name')
            except Semester.DoesNotExist:
                results = Result.objects.none()
                messages.error(request, 'Selected semester does not exist.')
        else:
            results = Result.objects.all().order_by('semester__semester_number', 'student__name', 'subject__name')
    else:
        try:
            student = Student.objects.get(user=request.user)
            all_results = Result.objects.filter(student=student).order_by('semester__semester_number', 'subject__name')
            if not all_results.exists():
                messages.error(request, 'No results found. Please contact the administrator.')
            else:
                paginator = Paginator(all_results, 4)
                page_number = request.GET.get('page', 1)
                try:
                    page_obj = paginator.page(page_number)
                    results = page_obj.object_list
                except PageNotAnInteger:
                    page_obj = paginator.page(1)
                    results = page_obj.object_list
                except EmptyPage:
                    page_obj = paginator.page(paginator.num_pages)
                    results = page_obj.object_list
        except Student.DoesNotExist:
            all_results = Result.objects.none()
            messages.error(request, 'No student profile found. Please contact the administrator.')
            results = all_results
    
    context = {
        'results': results,
        'students': students,
        'semesters': semesters,
        'student_selected': student_selected,
        'page_obj': page_obj,
    }
    return render(request, 'students/student_results.html', context)

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

@require_GET
@login_required
@user_passes_test(is_staff)
def get_students(request):
    lecture_id = request.GET.get('lecture_id')
    if not lecture_id:
        logger.warning("No lecture_id provided in get_students request")
        return JsonResponse({'error': 'Lecture ID is required'}, status=400)
    
    try:
        lecture = Lecture.objects.get(id=lecture_id)
        students = lecture.semester.enrollments.select_related('student').values(
            'student__id', 'student__name', 'student__enrollment_id'
        )
        logger.debug(f"Retrieved {students.count()} students for lecture {lecture_id}")
        
        response_data = {
            'students': list(students),
            'course_name': lecture.course.name,
            'lecture_date': lecture.lecture_date.strftime('%Y-%m-%d') if lecture.lecture_date else 'No Date'
        }
        return JsonResponse(response_data)
    except Lecture.DoesNotExist:
        logger.error(f"Lecture {lecture_id} not found")
        return JsonResponse({'error': 'Lecture not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching students for lecture {lecture_id}: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def attendance(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={request.path}")

    filter_form = AttendanceFilterForm(request.POST or None, user=request.user)
    formset = None
    lecture = None
    errors = {}
    student_filter = request.GET.get('student_filter', '')
    enrollment_filter = request.GET.get('enrollment_filter', '')
    subject_filter = request.GET.get('subject_filter', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    query_error = None

    if request.method == 'POST' and request.user.is_staff:
        if filter_form.is_valid():
            lecture = filter_form.cleaned_data['lecture']
            formset = AttendanceFormSet(
                request.POST,
                form_kwargs={'subject': lecture.subject, 'date': lecture.lecture_date}
            )
            logger.debug(f"Processing formset with {formset.total_form_count()} forms")
            if formset.is_valid():
                try:
                    for form in formset:
                        student = form.cleaned_data.get('student')
                        if not student:
                            logger.error(f"No student provided in form data: {form.cleaned_data}")
                            errors['formset_errors'] = errors.get('formset_errors', []) + [
                                {'index': formset.forms.index(form), 'errors': 'Student is required'}
                            ]
                            continue
                        status = form.cleaned_data.get('status')
                        if not status:
                            logger.error(f"No status provided in form data for student {student}: {form.cleaned_data}")
                            errors['formset_errors'] = errors.get('formset_errors', []) + [
                                {'index': formset.forms.index(form), 'errors': 'Status is required'}
                            ]
                            continue
                        student_id = student.id
                        logger.debug(f"Processing form for student ID {student_id} with cleaned_data: {form.cleaned_data}")
                        existing_attendance = Attendance.objects.filter(
                            student_id=student_id,
                            subject=lecture.subject,
                            date=lecture.lecture_date
                        ).first()
                        if existing_attendance:
                            existing_attendance.status = status
                            existing_attendance.save()
                            logger.debug(f"Updated attendance for student ID {student_id}, status: {status}")
                        else:
                            attendance = Attendance(
                                student_id=student_id,
                                subject=lecture.subject,
                                date=lecture.lecture_date,
                                status=status
                            )
                            attendance.save()
                            logger.debug(f"Saved new attendance for student ID {student_id}, status: {status}")
                    if not errors:
                        return JsonResponse({'success': True, 'message': 'Attendance recorded successfully'})
                except Exception as e:
                    logger.error(f"Error saving attendance: {str(e)}")
                    errors['formset_non_form_errors'] = [str(e)]
            else:
                errors['formset_errors'] = []
                for i, form in enumerate(formset.forms):
                    if form.errors:
                        logger.error(f"Form {i} errors: {form.errors}")
                        errors['formset_errors'].append({'index': i, 'errors': form.errors.as_text()})
                errors['formset_non_form_errors'] = formset.non_form_errors()
                logger.error(f"Formset non-form errors: {formset.non_form_errors()}")
        else:
            errors['filter_form_errors'] = [
                {'field': field, 'errors': error}
                for field, error in filter_form.errors.items()
            ]
            logger.error(f"Filter form errors: {filter_form.errors}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': errors}, status=400)

    if request.user.is_staff:
        attendance_records = Attendance.objects.all().select_related('student', 'subject')
        if student_filter:
            attendance_records = attendance_records.filter(student__name__icontains=student_filter)
        if enrollment_filter:
            attendance_records = attendance_records.filter(student__enrollment_id__icontains=enrollment_filter)
        if subject_filter:
            attendance_records = attendance_records.filter(subject__name__icontains=subject_filter)
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                attendance_records = attendance_records.filter(date__gte=start_date)
            except ValueError:
                logger.warning(f"Invalid start_date format: {start_date}")
                pass
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                attendance_records = attendance_records.filter(date__lte=end_date)
            except ValueError:
                logger.warning(f"Invalid end_date format: {end_date}")
                pass
        semesters = Semester.objects.filter(
            subjects__in=attendance_records.values('subject').distinct()
        ).select_related('course')
        semester_attendance = []
        for semester in semesters:
            records = attendance_records.filter(subject__semester=semester)
            records_paginator = Paginator(records, 10)
            records_page_number = request.GET.get(f'records_page_{semester.id}', 1)
            records_page = records_paginator.get_page(records_page_number)
            total_classes = records.count()
            present_classes = records.filter(status='P').count()
            semester_attendance.append({
                'semester': semester,
                'records': records_page,
                'records_paginator': records_paginator,
                'total_classes': total_classes,
                'present_classes': present_classes
            })
        paginator = Paginator(semester_attendance, 5)
        page_number = request.GET.get('page', 1)
        semester_attendance = paginator.get_page(page_number)
    else:
        student = get_object_or_404(Student, user=request.user)
        logger.debug(f"Fetching attendance for student: {student} (ID: {student.id}, Enrollment: {student.enrollment_id})")
        semester_attendance = []
        try:
            # Fetch attendance records directly
            attendance_records = Attendance.objects.filter(student=student).select_related('student', 'subject__semester')
            logger.debug(f"Found {attendance_records.count()} attendance records for student {student}")
            if attendance_records.exists():
                # Get unique semesters from attendance records
                semester_ids = attendance_records.values('subject__semester').distinct()
                semesters = Semester.objects.filter(id__in=semester_ids).select_related('course')
                logger.debug(f"Found semesters: {list(semesters)}")
                for semester in semesters:
                    records = attendance_records.filter(subject__semester=semester)
                    records_paginator = Paginator(records, 10)
                    records_page_number = request.GET.get(f'records_page_{semester.id}', 1)
                    records_page = records_paginator.get_page(records_page_number)
                    total_classes = records.count()
                    present_classes = records.filter(status='P').count()
                    semester_attendance.append({
                        'semester': semester,
                        'records': records_page,
                        'records_paginator': records_paginator,
                        'total_classes': total_classes,
                        'present_classes': present_classes
                    })
            else:
                logger.warning(f"No attendance records found for student {student}")
                query_error = "No attendance records found for this student."
        except Exception as e:
            logger.error(f"Error querying attendance for student {student}: {str(e)}")
            query_error = f"Error loading attendance records: {str(e)}. Please contact support."

        paginator = Paginator(semester_attendance, 5)
        page_number = request.GET.get('page', 1)
        semester_attendance = paginator.get_page(page_number)

    context = {
        'filter_form': filter_form,
        'formset': formset,
        'lecture': lecture,
        'semester_attendance': semester_attendance,
        'student_filter': student_filter,
        'enrollment_filter': enrollment_filter,
        'subject_filter': subject_filter,
        'start_date': start_date,
        'end_date': end_date,
        'query_error': query_error
    }
    return render(request, 'students/attendance.html', context)

@require_GET
@login_required
@user_passes_test(is_staff)
def get_students(request):
    lecture_id = request.GET.get('lecture_id')
    if lecture_id:
        try:
            lecture = Lecture.objects.get(id=lecture_id)
            students = Student.objects.filter(
                enrollments__course=lecture.course,
                enrollments__is_active=True
            ).values('id', 'name', 'enrollment_id').distinct()
            return JsonResponse({'students': list(students)})
        except (ValueError, Lecture.DoesNotExist):
            return JsonResponse({'students': [], 'error': 'Invalid lecture ID or lecture does not exist'}, status=400)
    return JsonResponse({'students': [], 'error': 'Lecture ID not provided'}, status=400)

@require_GET
@login_required
@user_passes_test(is_staff)
def get_lectures(request):
    course_id = request.GET.get('course_id')
    if course_id:
        try:
            course = Course.objects.get(id=course_id)
            # Get students enrolled in the course
            enrolled_students = Student.objects.filter(
                enrollments__course=course,
                enrollments__is_active=True
            ).distinct()
            # Get lectures where not all enrolled students have attendance recorded
            lectures = Lecture.objects.filter(course=course).select_related('subject').order_by('-lecture_date')
            filtered_lectures = []
            for lecture in lectures:
                attendance_count = Attendance.objects.filter(
                    subject=lecture.subject,
                    date=lecture.lecture_date,
                    student__in=enrolled_students
                ).count()
                if attendance_count < enrolled_students.count():
                    filtered_lectures.append({
                        'id': lecture.id,
                        'name': lecture.name,
                        'lecture_date': lecture.lecture_date.strftime('%d/%m/%Y')
                    })
            return JsonResponse({'lectures': filtered_lectures})
        except (ValueError, Course.DoesNotExist):
            return JsonResponse({'lectures': [], 'error': 'Invalid course ID or course does not exist'}, status=400)
    return JsonResponse({'lectures': [], 'error': 'Course ID not provided'}, status=400)


def lecture_page(request):
    if request.method == 'POST':
        form = LectureForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lecture added successfully!')
            return redirect('lecture')
        else:
            messages.error(request, 'Error adding lecture. Check your input.')
    else:
        form = LectureForm()

    lectures = Lecture.objects.select_related('course', 'semester', 'subject').all().order_by('lecture_date')
    context = {
        'form': form,
        'lectures': lectures,
    }
    return render(request, 'students/lecture.html', context)

@require_GET
@login_required
def get_semesters(request, course_id):
    try:
        semesters = Semester.objects.filter(course_id=course_id).values('id', 'semester_number')
        return JsonResponse({'semesters': list(semesters)})
    except Exception as e:
        logger.error(f"Error fetching semesters for course {course_id}: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@require_GET
@login_required
def get_subjects(request, semester_id):
    try:
        subjects = Subject.objects.filter(semester_id=semester_id).values('id', 'name')
        return JsonResponse({'subjects': list(subjects)})
    except Exception as e:
        logger.error(f"Error fetching subjects for semester {semester_id}: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
