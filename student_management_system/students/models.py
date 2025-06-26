from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum, Avg, Count, F, ExpressionWrapper, FloatField

def student_photo_path(instance, filename):
    return f'student_photos/{instance.enrollment_id}/{filename}'

def result_file_path(instance, filename):
    return f'results/{instance.student.enrollment_id}/{filename}'

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Course(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    name = models.CharField(max_length=100)
    duration_years = models.PositiveIntegerField(default=4)
    total_semesters = models.PositiveIntegerField(default=8)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('department', 'name')

    def __str__(self):
        return f"{self.name} - {self.department.name}"

class Semester(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='semesters')
    semester_number = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('course', 'semester_number')

    def __str__(self):
        return f"Semester {self.semester_number} - {self.course.name}"

class Subject(models.Model):
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    credits = models.PositiveIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code}: {self.name} (Semester {self.semester.semester_number})"

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    enrollment_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    date_of_birth = models.DateField()
    photo = models.ImageField(upload_to=student_photo_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.enrollment_id} - {self.name}"
    
    def get_current_semester(self):
        last_result = self.results.order_by('-semester__semester_number').first()
        return last_result.semester.semester_number if last_result else None

    def get_semester_results(self, semester_number):
        try:
            semester_number = int(semester_number)
            enrollment = self.enrollments.first()
            if not enrollment:
                return self.results.none()
            semester = Semester.objects.filter(
                course=enrollment.course,
                semester_number=semester_number
            ).first()
            if not semester:
                return self.results.none()
            return self.results.filter(semester=semester).order_by('subject__name')
        except (TypeError, ValueError):
            return self.results.none()

    def get_all_semesters_data(self):
        try:
            enrollment = self.enrollments.first()
            if not enrollment:
                return {}
            semesters = Semester.objects.filter(course=enrollment.course).order_by('semester_number')
            semester_ids = semesters.values_list('id', flat=True)
            results = self.results.filter(semester__id__in=semester_ids).annotate(
                subject_percentage=ExpressionWrapper(
                    F('marks') * 100.0 / F('total_marks'),
                    output_field=FloatField()
                )
            )
            semester_results = results.values('semester__semester_number').annotate(
                total_subjects=Count('id'),
                total_marks=Sum('total_marks'),
                obtained_marks=Sum('marks'),
                percentage=Avg('subject_percentage')
            ).order_by('semester__semester_number')
            return {
                str(sem['semester__semester_number']): {
                    'subjects_count': sem['total_subjects'],
                    'total_marks': float(sem['total_marks']) if sem['total_marks'] is not None else 0.0,
                    'obtained_marks': float(sem['obtained_marks']) if sem['obtained_marks'] is not None else 0.0,
                    'percentage': round(float(sem['percentage']), 2) if sem['percentage'] is not None else 0.0,
                    'grade': self.calculate_grade_from_percentage(sem['percentage'])
                }
                for sem in semester_results
            }
        except Exception:
            return {}

    @staticmethod
    def calculate_grade_from_percentage(percentage):
        if percentage is None:
            return 'F'
        try:
            percentage = float(percentage)
            if percentage >= 90:
                return 'A+'
            elif percentage >= 80:
                return 'A'
            elif percentage >= 70:
                return 'B+'
            elif percentage >= 60:
                return 'B'
            elif percentage >= 50:
                return 'C+'
            elif percentage >= 40:
                return 'C'
            else:
                return 'F'
        except (TypeError, ValueError):
            return 'F'

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    enrollment_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'department', 'course')

    def __str__(self):
        return f"{self.student.name} - {self.course.name if self.course else 'No Course'} ({self.department.name})"

class Result(models.Model):
    GRADE_CHOICES = [
        ('A+', 'A+ (90-100%)'),
        ('A', 'A (80-89%)'),
        ('B+', 'B+ (70-79%)'),
        ('B', 'B (60-69%)'),
        ('C+', 'C+ (50-59%)'),
        ('C', 'C (40-49%)'),
        ('F', 'F (Below 40%)'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='results')
    marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Marks obtained by the student"
    )
    total_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
        validators=[MinValueValidator(1)],
        help_text="Maximum marks for this subject"
    )
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES, blank=True)
    exam_date = models.DateField()
    result_file = models.FileField(upload_to=result_file_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('student', 'semester', 'subject')
        ordering = ['semester__semester_number', 'subject__name']
        verbose_name = "Academic Result"
        verbose_name_plural = "Academic Results"
    
    def __str__(self):
        return f"{self.student.name} - {self.subject.name} (Sem {self.semester.semester_number})"
    
    @property
    def percentage(self):
        try:
            percentage = (float(self.marks) / float(self.total_marks)) * 100
            return round(percentage, 2)
        except (ZeroDivisionError, TypeError, ValueError):
            return 0.00
    
    def clean(self):
        try:
            if float(self.marks) > float(self.total_marks):
                raise ValidationError('Marks obtained cannot be greater than total marks.')
            if self.subject.semester != self.semester:
                raise ValidationError('Subject must belong to the selected semester.')
            enrollment = self.student.enrollments.first()
            if enrollment and self.semester.course != enrollment.course and enrollment.course is not None:
                raise ValidationError('Semester must belong to the student’s enrolled course.')
        except (TypeError, ValueError):
            raise ValidationError('Invalid marks or total marks value.')

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.grade:
            self.grade = self.calculate_grade()
        super().save(*args, **kwargs)

    def calculate_grade(self):
        return Student.calculate_grade_from_percentage(self.percentage)

class FeeRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_records')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    payment_method = models.CharField(max_length=50, choices=[
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('bank', 'Bank Transfer'),
        ('upi', 'UPI Payment'),
        ('other', 'Other'),
    ], blank=True, default='')
    status = models.CharField(max_length=20, choices=[
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
    ], default='unpaid')
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_fees')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} - {self.amount} ({self.status})"

    class Meta:
        ordering = ['-payment_date']

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('P', 'Present'),
        ('A', 'Absent'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject', 'date')
        ordering = ['-date', 'subject__name']
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"

    def __str__(self):
        return f"{self.student.name} - {self.subject.name} ({self.date}) - {self.get_status_display()}"

    def get_attendance_percentage(self):
        """Calculate attendance percentage for this student in this subject."""
        total_classes = Attendance.objects.filter(
            student=self.student,
            subject=self.subject
        ).count()
        present_classes = Attendance.objects.filter(
            student=self.student,
            subject=self.subject,
            status='P'
        ).count()
        if total_classes == 0:
            return 0.0
        return round((present_classes / total_classes) * 100, 2)
    
class Lecture(models.Model):
    lecture_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lectures')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='lectures')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='lectures')
    lecture_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('course', 'semester', 'subject', 'lecture_id')
        ordering = ['lecture_date', 'subject__name']
        verbose_name = "Lecture"
        verbose_name_plural = "Lectures"

    def __str__(self):
        return f"{self.lecture_id}: {self.name} ({self.subject.name}, Sem {self.semester.semester_number})"

    def clean(self):
        try:
            if self.semester.course != self.course:
                raise ValidationError('Semester must belong to the selected course.')
            if self.subject.semester != self.semester:
                raise ValidationError('Subject must belong to the selected semester.')
        except (TypeError, ValueError):
            raise ValidationError('Invalid course, semester, or subject selection.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)