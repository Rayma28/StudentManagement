from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum, Avg, Count, F, ExpressionWrapper, FloatField

def student_photo_path(instance, filename):
    return f'student_photos/{instance.enrollment_id}/{filename}'

def result_file_path(instance, filename):
    return f'results/{instance.student.enrollment_id}/{filename}'

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
        """Get the highest semester the student has results for."""
        last_result = self.result_set.order_by('-semester').first()
        return last_result.semester if last_result else None

    def get_semester_results(self, semester):
        """Get results for a specific semester, leveraging model properties."""
        try:
            semester = str(semester)  # Ensure semester is a string for consistency
            return self.result_set.filter(semester=semester).order_by('subject')
        except (TypeError, ValueError):
            return self.result_set.none()  # Return empty queryset if semester is invalid

    def get_all_semesters_data(self):
        """Get aggregated data for all semesters with proper percentage calculation."""
        try:
            # Get all results with calculated percentages
            results = self.result_set.annotate(
                subject_percentage=ExpressionWrapper(
                    F('marks') * 100.0 / F('total_marks'),
                    output_field=FloatField()
                )
            )
            
            # Aggregate by semester
            semesters = results.values('semester').annotate(
                total_subjects=Count('id'),
                total_marks=Sum('total_marks'),
                obtained_marks=Sum('marks'),
                percentage=Avg('subject_percentage')
            ).order_by('semester')
            
            # Build dictionary with rounded percentages and consistent types
            return {
                str(sem['semester']): {
                    'subjects_count': sem['total_subjects'],
                    'total_marks': float(sem['total_marks']) if sem['total_marks'] is not None else 0.0,
                    'obtained_marks': float(sem['obtained_marks']) if sem['obtained_marks'] is not None else 0.0,
                    'percentage': round(float(sem['percentage']), 2) if sem['percentage'] is not None else 0.0,
                    'grade': self.calculate_grade_from_percentage(sem['percentage'])
                }
                for sem in semesters
            }
        except Exception:
            # Return empty dict if no results or error occurs
            return {}

    @staticmethod
    def calculate_grade_from_percentage(percentage):
        """Calculate grade based on percentage."""
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

class Result(models.Model):
    SEMESTER_CHOICES = [
        ('1', '1st Semester'),
        ('2', '2nd Semester'),
        ('3', '3rd Semester'),
        ('4', '4th Semester'),
        ('5', '5th Semester'),
        ('6', '6th Semester'),
        ('7', '7th Semester'),
        ('8', '8th Semester'),
    ]
    
    GRADE_CHOICES = [
        ('A+', 'A+ (90-100%)'),
        ('A', 'A (80-89%)'),
        ('B+', 'B+ (70-79%)'),
        ('B', 'B (60-69%)'),
        ('C+', 'C+ (50-59%)'),
        ('C', 'C (40-49%)'),
        ('F', 'F (Below 40%)'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    semester = models.CharField(max_length=1, choices=SEMESTER_CHOICES)
    subject = models.CharField(max_length=100)
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
        ordering = ['semester', 'subject']
        verbose_name = "Academic Result"
        verbose_name_plural = "Academic Results"
    
    def __str__(self):
        return f"{self.student.name} - {self.subject} (Sem {self.semester})"
    
    @property
    def percentage(self):
        """Calculate percentage with proper error handling."""
        try:
            percentage = (float(self.marks) / float(self.total_marks)) * 100
            return round(percentage, 2)
        except (ZeroDivisionError, TypeError, ValueError):
            return 0.00
    
    def clean(self):
        """Validate model data before saving."""
        try:
            if float(self.marks) > float(self.total_marks):
                raise ValidationError('Marks obtained cannot be greater than total marks.')
            if self.semester not in dict(self.SEMESTER_CHOICES).keys():
                raise ValidationError('Invalid semester selected.')
        except (TypeError, ValueError):
            raise ValidationError('Invalid marks or total marks value.')

    def save(self, *args, **kwargs):
        """Override save to auto-calculate grade and ensure data consistency."""
        self.full_clean()  # Run validation first
        if not self.grade:  # Only calculate if grade is not set
            self.grade = self.calculate_grade()
        super().save(*args, **kwargs)

    def calculate_grade(self):
        """Calculate grade based on percentage."""
        return Student.calculate_grade_from_percentage(self.percentage)
    
from django.db import models
from django.contrib.auth.models import User

class Fee(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='fees')
    semester = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Fee for {self.student} - Semester {self.semester}"