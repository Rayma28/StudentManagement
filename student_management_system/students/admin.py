from django.contrib import admin
from .models import Department, Course, Semester, Subject, Student, Enrollment, FeeRecord, Result, Attendance

admin.site.register(Attendance)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'total_semesters', 'created_at')
    list_filter = ('department',)
    search_fields = ('name',)

@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ('semester_number', 'course', 'created_at')
    list_filter = ('course',)
    search_fields = ('course__name',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'semester', 'credits', 'created_at')
    list_filter = ('semester__course', 'semester')
    search_fields = ('name', 'code')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'enrollment_id', 'email', 'is_active', 'created_at')
    search_fields = ('name', 'enrollment_id', 'email')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'department', 'course', 'enrollment_date', 'is_active')
    list_filter = ('department', 'course', 'is_active')
    search_fields = ('student__name',)

from django.contrib import admin
from .models import FeeRecord

@admin.register(FeeRecord)
class FeeAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'payment_date', 'status', 'payment_method')
    list_filter = ('status', 'payment_method', 'payment_date')
    search_fields = ('student__user__username', 'student__user__first_name', 'student__user__last_name')
    date_hierarchy = 'payment_date'
    ordering = ('-payment_date',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('student', 'amount', 'status')
        }),
        ('Dates', {
            'fields': ('payment_date', 'due_date')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'description')
        }),
    )
    
@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'semester', 'subject', 'grade', 'created_at')
    list_filter = ('semester', 'grade')
    search_fields = ('student__name', 'subject__name')