from django.contrib import admin
from .models import (
    Mahasiswa, Perusahaan, Supervisor, CoOpDetail, CoOpAccInfo, 
    Evaluation, EvaluationQuestion, EvaluationAnswer, 
    WeeklyReportSession, WeeklyReportQuestion, WeeklyReportAnswer, 
    FinalReport, Job, CoOpStatus # Impor semua Model
)

admin.site.register(Mahasiswa)
admin.site.register(Perusahaan)
admin.site.register(Supervisor)
admin.site.register(CoOpDetail)
admin.site.register(CoOpAccInfo)
admin.site.register(Evaluation)
admin.site.register(EvaluationQuestion)
admin.site.register(EvaluationAnswer)
admin.site.register(WeeklyReportSession)
admin.site.register(WeeklyReportQuestion)
admin.site.register(WeeklyReportAnswer)
admin.site.register(FinalReport)
admin.site.register(Job)
