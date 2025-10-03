from django.db import models
from django.contrib.auth.models import User

class Jeniskelamin(models.TextChoices):
    Pria = "Pria"
    Wanita = "Wanita"

class CoOpStatus(models.TextChoices):
    APPLYING = "applying", "Applying"
    PROGRESS = "progress", "On Progress"
    REPORT = "report", "Report Required"
    FINISHED = "finished", "Finished"

class Mahasiswa(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nim = models.CharField(max_length=11, primary_key=True)
    prodi = models.CharField(max_length=100)
    jeniskelamin = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=Jeniskelamin.choices, default=Jeniskelamin.Pria)
    angkatan = models.CharField(max_length=4)
    nomor_telepon = models.CharField(max_length=20)
    cv = models.FileField(upload_to="cv/", null=True, blank=True)
    portofolio = models.FileField(upload_to="portofolio/", null=True, blank=True)

    def __str__(self):
        return f"{self.nim} - {self.user.get_full_name()}"

class Perusahaan(models.Model):
    company_id = models.AutoField(primary_key=True)
    nama = models.CharField(max_length=200)
    alamat = models.TextField()
    bidang = models.CharField(max_length=200)

    def __str__(self):
        return self.nama

class Supervisor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    supervisor_id = models.AutoField(primary_key=True)
    perusahaan = models.ForeignKey(Perusahaan, on_delete=models.CASCADE)
    nama = models.CharField(max_length=200)
    email = models.EmailField()
    nomor_telepon = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.nama} ({self.perusahaan.nama})"

class CoOpDetail(models.Model):
    mahasiswa = models.OneToOneField(Mahasiswa, on_delete=models.CASCADE)
    supervisor = models.ForeignKey(Supervisor, on_delete=models.CASCADE)
    posisi = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=CoOpStatus.choices, default=CoOpStatus.APPLYING)

    def __str__(self):
        return f"{self.mahasiswa.nim} - {self.supervisor.perusahaan.nama}" 

class CoOpAccInfo(models.Model):
    mahasiswa = models.OneToOneField(Mahasiswa, on_delete=models.CASCADE)
    proofmentor = models.FileField(upload_to="proof_mentor/")
    proofsptjm = models.FileField(upload_to="sptjm/")

class EvaluationQuestion(models.Model):
    question = models.TextField()

    def __str__(self):
        return self.question[:50]

class EvaluationForm(models.Model):
    title = models.CharField(max_length=255)
    target_angkatan = models.CharField(max_length=255, help_text="e.g. 2021,2022")
    questions = models.ManyToManyField(EvaluationQuestion)
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False) 
    
    def __str__(self):
        return self.title

class Evaluation(models.Model):
    mahasiswa = models.ForeignKey(Mahasiswa, on_delete=models.CASCADE)
    supervisor = models.ForeignKey(Supervisor, on_delete=models.CASCADE)
    evaluation_form = models.ForeignKey(EvaluationForm, on_delete=models.CASCADE) 
    tanggal = models.DateField(auto_now_add=True)
    is_filled = models.BooleanField(default=False)

    def __str__(self):
        return f"Evaluation of {self.mahasiswa.nim} ({self.evaluation_form.title})"

class EvaluationAnswer(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
    question = models.ForeignKey(EvaluationQuestion, on_delete=models.CASCADE)
    answer = models.TextField()


class WeeklyReportQuestion(models.Model):
    question = models.TextField()

    def __str__(self):
        return self.question[:50]

class WeeklyReportSession(models.Model):
    mahasiswa = models.ForeignKey(Mahasiswa, on_delete=models.CASCADE)
    minggu_ke = models.IntegerField(default=1) 
    tanggal = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Weekly Report Week-{self.minggu_ke} by {self.mahasiswa.nim}"

class WeeklyReportAnswer(models.Model):
    session = models.ForeignKey(WeeklyReportSession, on_delete=models.CASCADE)
    jobdesk = models.TextField()
    suasana = models.TextField()
    ilmu_berguna = models.TextField()
    ilmu_kurang = models.TextField()
    
    def __str__(self):
        return f"Answer for {self.session}"

class FinalReport(models.Model):
    mahasiswa = models.OneToOneField(Mahasiswa, on_delete=models.CASCADE)
    filereport = models.FileField(upload_to="final_reports/")
    tanggal_upload = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Final Report of {self.mahasiswa.nim}"

class Job(models.Model):
    job_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    description = models.TextField()
    links = models.TextField()
    media = models.FileField(upload_to="jobmedia/", null=True, blank=True)

    def __str__(self):
        return str(self.title)

class PlacementStatus(models.TextChoices):
    PENDING_PLACEMENT = "pending_placement", "Pending Placement Confirmation"
    CONFIRMED = "confirmed", "Confirmed Placement"

class CoOpRegistration(models.Model):
    mahasiswa = models.OneToOneField(Mahasiswa, on_delete=models.CASCADE, primary_key=True)
    registration_date = models.DateField(auto_now_add=True)
    placement_status = models.CharField(max_length=50, choices=PlacementStatus.choices, default=PlacementStatus.PENDING_PLACEMENT)
    placement_deadline = models.DateField(null=True, blank=True) 
    
class NoPlacementReport(models.Model):
    pass

class ApplicationStatus(models.TextChoices):
    PENDING = "pending", "Pending Review"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"

class JobApplication(models.Model):
    mahasiswa = models.ForeignKey(Mahasiswa, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    application_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.PENDING)

    class Meta:
        unique_together = ('mahasiswa', 'job')
