from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('profile/', views.student_profile, name='student_profile'),
    path('upload-result/', views.upload_result, name='upload_result'),
    path('get_subjects/<int:semester_id>/', views.get_subjects, name='get_subjects'),
    path('all-students/', views.all_students, name='all_students'),
    path('student/<str:enrollment_id>/', views.student_detail, name='student_detail'),
    path('results/', views.student_results, name='student_results'),
    path('my-fees/', views.my_fees, name='my_fees'),
    path('fees/add/', views.add_fee_record, name='add_fee_record'),
    path('fees/edit/<int:pk>/', views.edit_fee_record, name='edit_fee_record'),
    path('fees/delete/<int:pk>/', views.delete_fee_record, name='delete_fee_record'),
    path('attendance/', views.attendance, name='attendance'),
    path('get-students/', views.get_students, name='get_students'),
    path('get-lectures/', views.get_lectures, name='get_lectures'),
    path('departments/', views.department_view, name='departments'),
    path('departments/delete/<int:dept_id>/', views.delete_department, name='delete_department'),
    path('courses/', views.course_view, name='courses'),
    path('courses/delete/<int:course_id>/', views.delete_course, name='delete_course'),
    path('semesters/', views.semester_view, name='semesters'),
    path('semesters/delete/<int:semester_id>/', views.delete_semester, name='delete_semester'),
    path('subjects/', views.subject_view, name='subjects'),
    path('subjects/delete/<int:subject_id>/', views.delete_subject, name='delete_subject'),
    path('enrollments/', views.enrollment_view, name='enrollments'),
    path('enrollments/delete/<int:enrollment_id>/', views.delete_enrollment, name='delete_enrollment'),
    path('student/<str:enrollment_id>/attendance/', views.student_attendance, name='student_attendance'),
    path('lectures/', views.lecture_page, name='lecture'),
    path('get_semesters/<int:course_id>/', views.get_semesters, name='get_semesters'),
    path('get_subjects/<int:semester_id>/', views.get_subjects, name='get_subjects'),
]
