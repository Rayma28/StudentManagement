from . import views
from django.urls import path


urlpatterns = [
    path('profile/', views.student_profile, name='student_profile'),
    path('upload-result/', views.upload_result, name='upload_result'),
    path('all-students/', views.all_students, name='all_students'),
    path('student/<str:enrollment_id>/', views.student_detail, name='student_detail'),
    path('departments/', views.department_view, name='department'),
    path('results/', views.student_results, name='student_results'),
    path('my-fees/', views.my_fees, name='my_fees'),
    path('fees/add/', views.add_fee_record, name='add_fee_record'),
    path('fees/edit/<int:pk>/', views.edit_fee_record, name='edit_fee_record'),
    path('fees/delete/<int:pk>/', views.delete_fee_record, name='delete_fee_record'),
]
