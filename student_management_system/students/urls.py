from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.student_profile, name='student_profile'),
    path('results/', views.student_results, name='student_results'),
    path('upload-result/', views.upload_result, name='upload_result'),
    path('all-students/', views.all_students, name='all_students'),
    path('student/<str:enrollment_id>/', views.student_detail, name='student_detail'),
    path('fees/', views.fees_view, name='fees'),
    path('fees/add/', views.add_fee, name='add_fee'),
    path('fees/update/<int:fee_id>/', views.update_fee, name='update_fee'),
]
