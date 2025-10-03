from django.urls import path
from . import views

urlpatterns = [
    path('', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    
    path('hpadmin/', views.hp_admin, name='hp_admin'),
    path('hpmahasiswa/', views.hp_mahasiswa, name='hp_mahasiswa'),
    path('hpsupervisor/', views.hp_supervisor, name='hp_supervisor'),
    
    path('mahasiswa/send_feedback/', views.send_mail, name='send_mail'),
    path('mahasiswa/applications/status/', views.job_application_status_list, name='application_status'),
    path('mahasiswa/apply/<int:job_id>/', views.apply_to_job, name='apply_to_job'),
    
    path('registcoop/', views.registcoop, name='regist_coop'),
    path('updateinternstatus/', views.updateinternstat, name='updateinternstat'),
    path('weeklyreport/fill/', views.fill_weekly_report, name='fill_weekly_report'),
    path('finalreport/submit/', views.submit_final_report, name='submit_final_report'),

    path('certificate/generate/', views.generate_certificate_pdf, name='generate_certificate_pdf'),
    path('certificate/download/', views.download_certificate, name='download_certificate'),

    path('mahasiswa/<str:nim>/details/', views.student_detail, name='student_detail'),
    path('mahasiswa/<str:nim>/', views.detail_mahasiswa, name='detail_mahasiswa'),
    
    path('admin/students/', views.student_list, name='student_list'),
    path('admin/jobs/upload/', views.upload_job_opportunity, name='upload_job_opportunity'),

    path('admin/evaluation/create/', views.create_evaluation, name='create_evaluation'),
    path('admin/evaluation/all/', views.evaluation_summary_list, name='evaluation_summary_list'),
    path('admin/evaluation/form/<int:form_id>/', views.evaluation_form_detail, name='evaluation_form_detail'), 
    path('evaluation/fill/<int:form_id>/<str:nim>/', views.fill_evaluation_form, name='fill_evaluation_form'),
    
    path('admin/evaluation/download/all/<int:evaluation_id>/', views.download_all_evaluations_pdf, name='download_all_evaluations_pdf'),

    path('admin/reports/weekly/', views.weekly_report_list, name='weekly_report_list'), 
    path('admin/reports/weekly/<int:session_id>/', views.weekly_report_detail, name='weekly_report_detail'),
    path('admin/reports/final/', views.final_report_list, name='final_report_list'),
    path('admin/reports/final/<str:nim>/download/', views.download_final_report, name='download_final_report'),

    path('evaluation/<int:evaluation_id>/download/', views.download_evaluation_pdf, name='download_evaluation_pdf'),
    
]