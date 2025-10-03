from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from .models import Mahasiswa, Evaluation, CoOpDetail, Job, CoOpAccInfo, Perusahaan, Supervisor, FinalReport, EvaluationQuestion, WeeklyReportSession, WeeklyReportAnswer
from .models import EvaluationForm, EvaluationAnswer, CoOpRegistration, NoPlacementReport, PlacementStatus, JobApplication, ApplicationStatus, Evaluation
from datetime import date
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, FileResponse, Http404 
from django.db.models import Count, Q, Prefetch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas

def login(request):
    if request.method == "POST":
        email = request.POST.get("username")
        password = request.POST.get("password")

        try:
            user_obj = User.objects.get(email__iexact=email)
            username_to_auth = user_obj.username
            password_to_auth = password
            
            if not email.endswith("@student.prasetiyamulya.ac.id") and not email.startswith("admincoop"):
                expected_password = email.split('@')[0]
                if password.lower() != expected_password.lower():
                     user_obj.set_password(expected_password)
                     user_obj.save()
                     
                password_to_auth = expected_password
                
            user = authenticate(request, username=username_to_auth, password=password_to_auth)
            
        except User.DoesNotExist:
            user = None
        
        except Exception as e:
            user = None

        if user is not None:
            auth_login(request, user)

            if email.endswith("@student.prasetiyamulya.ac.id"):
                return redirect('hp_mahasiswa')
            elif email.startswith("admincoop"):
                return redirect('hp_admin')
            elif user == "supervisor":
                return redirect('hp_supervisor')
            else:
                return redirect('hp_supervisor')

        else:
            messages.error(request, "Email atau password salah!")
            return render(request, 'utsCoop/login.html')

    return render(request, 'utsCoop/login.html')

def logout(request):
    auth_logout(request)
    return redirect('login')

def signup(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email sudah terdaftar!")
        else:
            user = User.objects.create_user(username=email, email=email, password=password)
            user.save()
            auth_login(request, user)
            return redirect('/')

    return render(request, 'utsCoop/signup.html')

def hp_admin(request):
    mahasiswa_list = Mahasiswa.objects.all()[:9]

    all_evaluation_forms = EvaluationForm.objects.filter(is_published=True).order_by('-created_at') 
    
    evaluation_summary_list = []

    for form in all_evaluation_forms:

        total_evaluations = Evaluation.objects.filter(evaluation_form=form)
        
        total_count = total_evaluations.count()
        filled_count = total_evaluations.filter(is_filled=True).count()
        pending_count = total_count - filled_count
        
        evaluation_summary_list.append({
            'title': form.title,
            'form_id': form.id, 
            'total_count': total_count,
            'filled_count': filled_count,
            'pending_count': pending_count,
        })
        
    evaluation_summary_list = evaluation_summary_list[:3]

    context = {
        'mahasiswa_list': mahasiswa_list, 
        'evaluation_summary_list': evaluation_summary_list,
    }

    return render(request, 'utsCoop/HPadmin.html', context)

def hp_mahasiswa(request):
    user = request.user
    mahasiswa_data = None
    coop_detail_data = None
    coop_status = 'NOT_REGISTERED' 
    today = date.today()

    if user.is_authenticated and user.email.endswith("@student.prasetiyamulya.ac.id"):
        try:
            mahasiswa_data = Mahasiswa.objects.get(user=user)
            coop_status = 'REGISTERED' 
            
            # Cek status magang
            try:
                coop_detail_data = CoOpDetail.objects.get(mahasiswa=mahasiswa_data)
                
                if coop_detail_data.status == 'finished' or coop_detail_data.end_date < today:
                    coop_status = 'FINISHED'
                else:
                    coop_status = 'ON_INTERNSHIP' 
            except CoOpDetail.DoesNotExist:
                coop_status = 'REGISTERED' 
            
            # --- LOGIC REMINDER NON-PENEMPATAN DIHAPUS DARI SINI ---
            # Data CoOpRegistration tetap perlu diambil untuk context, jika ada
            try:
                registration_info = CoOpRegistration.objects.get(mahasiswa=mahasiswa_data)
            except CoOpRegistration.DoesNotExist:
                registration_info = None

        except Mahasiswa.DoesNotExist:
            coop_status = 'NOT_REGISTERED'
            pass 
    
    if not user.is_authenticated or not user.email.endswith("@student.prasetiyamulya.ac.id"):
        return redirect('login') 

    job_list = Job.objects.all().order_by('-job_id') 

    context = {
        'user_data': user,
        'mahasiswa_data': mahasiswa_data,
        'coop_status': coop_status,
        'job_list': job_list,
        # Variabel reminder tidak lagi dibutuhkan di context
    }
    return render(request, 'utsCoop/HPmahasiswa.html', context)

def hp_supervisor(request):
    if not request.user.is_authenticated:
        messages.error(request, "Silakan login terlebih dahulu.")
        return redirect('login')
    
    try:
        current_supervisor = Supervisor.objects.get(user=request.user)
    except Supervisor.DoesNotExist:
        messages.error(request, "Akses ditolak. Akun Anda tidak terdaftar sebagai Supervisor.")
        return redirect('logout') 

    supervised_students = Mahasiswa.objects.filter(
        coopdetail__supervisor=current_supervisor
    ).select_related('user').order_by('nim')

    pending_evaluations = Evaluation.objects.filter(
        supervisor=current_supervisor,
        is_filled=False
    ).select_related('mahasiswa__user', 'evaluation_form')
    
    context = {
        'supervisor': current_supervisor,
        'supervised_students': supervised_students,
        'pending_evaluations': pending_evaluations, 
    }

    return render(request, 'utsCoop/HPsupervisor.html', context)

def detail_mahasiswa(request, nim):
    mahasiswa = get_object_or_404(Mahasiswa, nim=nim) 
    return render(request, 'utsCoop/student_detail.html', {'mahasiswa': mahasiswa}) 

def registcoop(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user
    
    try:
        mahasiswa_data = Mahasiswa.objects.get(user=user)
        messages.info(request, "Anda sudah terdaftar dalam Program Co-Op.")
        return redirect('hp_mahasiswa')
    except Mahasiswa.DoesNotExist:
        mahasiswa_data = None

    context = {
        'user_data': user,
        'mahasiswa_data': mahasiswa_data,
        'coop_status': 'NOT_REGISTERED',
    }

    if request.method == "POST":
        
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        nim = request.POST.get("nim")
        prodi = request.POST.get("prodi")
        angkatan = request.POST.get("angkatan")
        jenis_kelamin = request.POST.get("jenis_kelamin")
        nomor_telepon = request.POST.get("nomor_telepon")
        
        proofmentor = request.FILES.get("proofmentor")
        proofsptjm = request.FILES.get("proofsptjm")
        cv_file = request.FILES.get("cv")
        portfolio_file = request.FILES.get("portfolio")
        
        required_fields = [first_name, last_name, nim, prodi, angkatan, jenis_kelamin, nomor_telepon]
        
        if not all(required_fields) or not proofmentor or not proofsptjm or not cv_file or not portfolio_file:
            messages.error(request, "Semua field dan file upload harus diisi!")
            return render(request, 'utsCoop/register_coop.html', context)
        
        if Mahasiswa.objects.filter(nim=nim).exists():
            messages.error(request, f"NIM {nim} sudah terdaftar!")
            return render(request, 'utsCoop/register_coop.html', context)
        
        try:
            with transaction.atomic():
                user.first_name = first_name
                user.last_name = last_name
                user.save()

                new_mahasiswa = Mahasiswa.objects.create(
                    user=user,
                    nim=nim,
                    prodi=prodi,
                    angkatan=angkatan,
                    jeniskelamin=jenis_kelamin, 
                    nomor_telepon=nomor_telepon,
                    cv=cv_file,
                    portofolio=portfolio_file,
                )
                
                CoOpAccInfo.objects.create(
                    mahasiswa=new_mahasiswa,
                    proofmentor=proofmentor,
                    proofsptjm=proofsptjm,
                )

                messages.success(request, "Registrasi Co-Op berhasil! Silakan cek status aplikasi Anda.")
                return redirect('hp_mahasiswa')

        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat menyimpan data: {e}")
            return render(request, 'utsCoop/Registercoop.html', context)

    return render(request, 'utsCoop/Registercoop.html', context)

def updateinternstat(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user
    
    try:
        mahasiswa = Mahasiswa.objects.get(user=user)
    except Mahasiswa.DoesNotExist:
        messages.error(request, "Anda belum menyelesaikan registrasi Co-Op dasar.")
        return redirect('regist_coop')

    if CoOpDetail.objects.filter(mahasiswa=mahasiswa).exists():
        messages.info(request, "Status magang Anda sudah tercatat.")
        return redirect('hp_mahasiswa')
        
    context = {
        'user_data': user,
        'mahasiswa': mahasiswa,
    }

    if request.method == "POST":
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        posisi = request.POST.get("posisi")
        proof_acceptance = request.FILES.get("proof_acceptance")
        
        company_name = request.POST.get("company_name")
        company_bidang = request.POST.get("company_bidang")
        company_address = request.POST.get("company_address")
        
        supervisor_name = request.POST.get("supervisor_name")
        supervisor_email = request.POST.get("supervisor_email")
        supervisor_phone = request.POST.get("supervisor_phone")

        required_fields = [start_date, end_date, posisi, company_name, company_bidang, company_address, supervisor_name, supervisor_email]
        
        if not all(required_fields) or not proof_acceptance:
            messages.error(request, "Semua field wajib diisi, termasuk Bukti Penerimaan!")
            return render(request, 'utsCoop/update_internship_status.html', context)
        
        try:
            with transaction.atomic():
                company, created_company = Perusahaan.objects.get_or_create(
                    nama=company_name,
                    defaults={
                        'alamat': company_address,
                        'bidang': company_bidang,
                    }
                )

                supervisor_username_part = supervisor_email.split('@')[0]
                
                supervisor_user, created_supervisor_user = User.objects.get_or_create(
                    email=supervisor_email,
                    defaults={
                        'username': supervisor_email.split('@')[0] + "_coop",
                        'first_name': supervisor_name,
                        'is_staff': True,
                    }
                )

                if created_supervisor_user or not supervisor_user.has_usable_password():
                    supervisor_user.set_password(supervisor_username_part) 
                    supervisor_user.save()
                
                supervisor_obj, created_supervisor = Supervisor.objects.get_or_create(
                    user=supervisor_user,
                    defaults={
                        'perusahaan': company,
                        'nama': supervisor_name,
                        'email': supervisor_email,
                        'nomor_telepon': supervisor_phone,
                    }
                )

                coop_acc_info = CoOpAccInfo.objects.get(mahasiswa=mahasiswa)
                coop_acc_info.proofmentor = proof_acceptance
                coop_acc_info.save()
                
                CoOpDetail.objects.create(
                    mahasiswa=mahasiswa,
                    supervisor=supervisor_obj,
                    posisi=posisi,
                    start_date=start_date,
                    end_date=end_date,
                )

                try:
                    reg_info = CoOpRegistration.objects.get(mahasiswa=mahasiswa)
                    reg_info.placement_status = PlacementStatus.CONFIRMED
                    reg_info.save()
                except CoOpRegistration.DoesNotExist:
                    CoOpRegistration.objects.create(
                        mahasiswa=mahasiswa,
                        placement_status=PlacementStatus.CONFIRMED,
                        placement_deadline=date.today()
                    )
                
                messages.success(request, "Status Internship berhasil diperbarui!")
                return redirect('hp_mahasiswa')

        except Exception as e:
            messages.error(request, f"Gagal menyimpan status magang: {e}")
            return render(request, 'utsCoop/Updateinternstatus.html', context)

    return render(request, 'utsCoop/Updateinternstatus.html', context)

def student_detail(request, nim):
    mahasiswa = get_object_or_404(Mahasiswa, nim=nim)

    try:
        coop_detail = CoOpDetail.objects.select_related('supervisor__perusahaan').get(mahasiswa=mahasiswa)
    except CoOpDetail.DoesNotExist:
        coop_detail = None

    context = {
        'mahasiswa': mahasiswa,
        'coop_detail': coop_detail,
    }
    return render(request, 'utsCoop/student_detail.html', context)

def fill_weekly_report(request):
    if not request.user.is_authenticated:
        return redirect('login')
    user = request.user

    try:
        mahasiswa = Mahasiswa.objects.get(user=user)
        coop_detail = CoOpDetail.objects.select_related('supervisor__perusahaan').get(mahasiswa=mahasiswa) 
    except Mahasiswa.DoesNotExist:
        messages.error(request, "Anda harus mendaftar Co-Op terlebih dahulu.")
        return redirect('regist_coop')
    except CoOpDetail.DoesNotExist:
        messages.error(request, "Status magang Anda belum diatur.")
        return redirect('updateinternstat')
    
    context = {
        'user_data': user,
        'mahasiswa_data': mahasiswa,
        'detail_magang': coop_detail,
    }

    if request.method == "POST":
        messages.success(request, "Laporan Mingguan berhasil dikirim!")
        return redirect('hp_mahasiswa')

    return render(request, 'utsCoop/weeklyreport.html', context)

def submit_final_report(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user
    
    try:
        mahasiswa = Mahasiswa.objects.get(user=user)
    except Mahasiswa.DoesNotExist:
        messages.error(request, "Anda harus mendaftar Co-Op terlebih dahulu.")
        return redirect('regist_coop')

    try:
        CoOpDetail.objects.get(mahasiswa=mahasiswa)
    except CoOpDetail.DoesNotExist:
        messages.error(request, "Silakan atur status magang Anda terlebih dahulu.")
        return redirect('updateinternstat')

    context = {
        'user_data': user,
        'mahasiswa_data': mahasiswa,
    }

    if request.method == "POST":
        filereport = request.FILES.get("filereport")

        if not filereport:
            messages.error(request, "Anda harus memilih file Laporan Akhir.")
            return render(request, 'utsCoop/submit_final_report.html', context)
        
        if FinalReport.objects.filter(mahasiswa=mahasiswa).exists():
            messages.warning(request, "Laporan Akhir sudah pernah di-submit dan akan ditimpa (overwritten).")
            final_report_obj = FinalReport.objects.get(mahasiswa=mahasiswa)
            final_report_obj.filereport = filereport
            final_report_obj.save()
        else:
            FinalReport.objects.create(
                mahasiswa=mahasiswa,
                filereport=filereport
            )

        messages.success(request, "Laporan Akhir berhasil disubmit!")
        return redirect('hp_mahasiswa')

    return render(request, 'utsCoop/finalreport.html', context)

def download_certificate(request):
    user = request.user
    
    if not user.is_authenticated:
        return redirect('login')
        
    try:
        mahasiswa = Mahasiswa.objects.get(user=user)
        coop_detail = CoOpDetail.objects.get(mahasiswa=mahasiswa)

        if coop_detail.end_date > date.today():
             messages.error(request, "Sertifikat belum tersedia. Periode magang belum berakhir.")
             return redirect('hp_mahasiswa')

    except (Mahasiswa.DoesNotExist, CoOpDetail.DoesNotExist):
         messages.error(request, "Data tidak ditemukan.")
         return redirect('hp_mahasiswa')

    return render(request, 'utsCoop/download_certificate.html')

def generate_certificate_pdf(request):
    user = request.user
    
    if not user.is_authenticated:
        return HttpResponse("Akses ditolak.", status=403)
        
    try:
        mahasiswa = Mahasiswa.objects.get(user=user)
        coop_detail = CoOpDetail.objects.get(mahasiswa=mahasiswa)
        
        if coop_detail.end_date > date.today():
             return HttpResponse("Sertifikat belum tersedia.", status=403)

    except (Mahasiswa.DoesNotExist, CoOpDetail.DoesNotExist):
         return HttpResponse("Data Mahasiswa atau Co-Op tidak ditemukan.", status=404)

    student_name = mahasiswa.user.get_full_name()
    company_name = coop_detail.supervisor.perusahaan.nama
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Sertifikat_CoOp_{mahasiswa.nim}.pdf"'
    
    pdf_content = f"""
    Sertifikat Co-Op
    Diberikan kepada: {student_name} ({mahasiswa.nim})
    Telah menyelesaikan magang di: {company_name}
    Periode: {coop_detail.start_date} hingga {coop_detail.end_date}
    """
    
    response.write(pdf_content.encode('utf-8'))
    return response

def create_evaluation(request):
    if not request.user.is_authenticated or not request.user.email.startswith("admincoop"):
        messages.error(request, "Akses ditolak.")
        return redirect('hp_admin')

    questions = EvaluationQuestion.objects.all()
    angkatan_list = Mahasiswa.objects.values_list('angkatan', flat=True).distinct().order_by('-angkatan')
    active_forms = EvaluationForm.objects.all().order_by('-created_at')

    context = {
        'questions': questions,
        'angkatan_list': angkatan_list,
        'active_forms': active_forms,
    }

    if request.method == 'POST':

        if 'add_question_btn' in request.POST:
            question_text = request.POST.get('new_question_text', '').strip()
            if question_text:
                try:
                    with transaction.atomic():
                        EvaluationQuestion.objects.create(question=question_text)
                    messages.success(request, f"Pertanyaan baru '...{question_text[:30]}...' berhasil ditambahkan. Silakan pilih dan publikasikan form.")
                except Exception as e:
                    messages.error(request, f"Gagal menambahkan pertanyaan: {e}")
            else:
                messages.warning(request, "Pertanyaan tidak boleh kosong.")
            return redirect('create_evaluation')

        elif 'publish_form' in request.POST:
            title = request.POST.get('title', '').strip()
            selected_questions_ids = request.POST.getlist('selected_questions[]') 
            target_angkatan_list = request.POST.getlist('target_angkatan[]')

            if not title or not selected_questions_ids or not target_angkatan_list:
                messages.error(request, "Gagal. Harap isi Judul, pilih Pertanyaan, dan target Angkatan!")
                return render(request, 'utsCoop/create_eval.html', context)

            try:
                with transaction.atomic():
                    target_angkatan_str = ",".join(target_angkatan_list)

                    new_form = EvaluationForm.objects.create(
                        title=title,
                        target_angkatan=target_angkatan_str,
                        is_published = True
                    )

                    int_question_ids = [int(q_id) for q_id in selected_questions_ids]
                    new_form.questions.set(int_question_ids)

                    target_mahasiswa_with_coop = Mahasiswa.objects.filter(
                        angkatan__in=target_angkatan_list,
                        coopdetail__isnull=False 
                    ).select_related('coopdetail__supervisor')
                    
                    evaluations_created = 0
                    
                    for mhs in target_mahasiswa_with_coop:
                        supervisor_obj = mhs.coopdetail.supervisor
                        
                        if not Evaluation.objects.filter(
                            mahasiswa=mhs, 
                            supervisor=supervisor_obj, 
                            evaluation_form=new_form
                        ).exists():
                            
                            Evaluation.objects.create(
                                mahasiswa=mhs,
                                supervisor=supervisor_obj,
                                evaluation_form=new_form,
                                is_filled=False
                            )
                            evaluations_created += 1

                if evaluations_created == 0:
                     messages.warning(request, f"Formulir Evaluasi '{title}' berhasil dipublikasikan, namun **0** evaluasi dikirim. Pastikan ada Mahasiswa di Angkatan target yang sedang atau sudah magang.")
                else:
                     messages.success(request, f"Formulir Evaluasi '{title}' berhasil dipublikasikan. ({evaluations_created} tugas evaluasi telah dikirim ke Supervisor terkait).")
                
                return redirect('hp_admin')

            except Exception as e:
                messages.error(request, f"Terjadi Kesalahan Server saat publikasi: {e}. Cek koneksi DB dan pastikan data Mahasiswa/CoOpDetail lengkap.")
                return render(request, 'utsCoop/create_eval.html', context)

    return render(request, 'utsCoop/create_eval.html', context)

def student_list(request):
    if not request.user.is_authenticated or not request.user.email.startswith("admincoop"):
        messages.error(request, "Akses ditolak.")
        return redirect('hp_admin')
        
    mahasiswa_list = Mahasiswa.objects.select_related('user', 'coopdetail').all().order_by('nim')
    
    context = {
        'mahasiswa_list': mahasiswa_list
    }
    return render(request, 'utsCoop/student_list.html', context)

def evaluation_summary_list(request):
    if not request.user.is_authenticated or not request.user.email.startswith("admincoop"):
        messages.error(request, "Akses ditolak.")
        return redirect('hp_admin')

    forms = EvaluationForm.objects.filter(is_published=True).order_by('-created_at')
    
    evaluation_summary_list = []

    for form in forms:
        total_count = Evaluation.objects.filter(evaluation_form=form).count()
        
        filled_count = Evaluation.objects.filter(evaluation_form=form, is_filled=True).count()
        
        pending_count = total_count - filled_count
        
        evaluation_summary_list.append({
            'title': form.title,
            'form_id': form.id,
            'total_count': total_count,
            'filled_count': filled_count,
            'pending_count': pending_count,
        })

    context = {
        'evaluation_summary_list': evaluation_summary_list,
    }
    
    return render(request, 'utsCoop/evaluation_details.html', context)

def evaluation_form_detail(request, form_id):
    evaluation_form = get_object_or_404(EvaluationForm, pk=form_id)

    evaluations = Evaluation.objects.filter(evaluation_form=evaluation_form).order_by('mahasiswa__nim').select_related(
        'mahasiswa__user', 
        'supervisor', 
        'supervisor__perusahaan'
    )
    
    context = {
        'evaluation_form': evaluation_form,
        'evaluations': evaluations,
    }

    return render(request, 'utsCoop/evaluation_form_detail.html', context)

def fill_evaluation_form(request, form_id, nim):
    if not request.user.is_authenticated or request.user.email.endswith("@student.prasetiyamulya.ac.id"):
        messages.error(request, "Akses ditolak. Hanya Supervisor atau Admin yang dapat mengisi evaluasi.")
        return redirect('login')
    
    evaluation_form = get_object_or_404(EvaluationForm, pk=form_id)
    mahasiswa = get_object_or_404(Mahasiswa, nim=nim)
    
    try:
        current_supervisor = Supervisor.objects.get(user=request.user)
    except Supervisor.DoesNotExist:
        if request.user.email.startswith("admincoop"):
            try:
                coop_detail = CoOpDetail.objects.get(mahasiswa=mahasiswa)
                current_supervisor = coop_detail.supervisor
            except CoOpDetail.DoesNotExist:
                messages.error(request, f"Tidak ada detail magang atau supervisor untuk {mahasiswa.nim}.")
                return redirect('hp_supervisor')
        else:
            messages.error(request, "Akun Anda tidak terdaftar sebagai Supervisor.")
            return redirect('hp_supervisor')
        
    if Evaluation.objects.filter(
        mahasiswa=mahasiswa, 
        evaluation_form=evaluation_form, 
        supervisor=current_supervisor,
        is_filled=True
    ).exists():
        messages.warning(request, "Formulir evaluasi ini sudah Anda isi untuk mahasiswa tersebut.")
        return redirect('hp_supervisor')
    
    questions = evaluation_form.questions.all().order_by('pk')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                evaluation_obj, created = Evaluation.objects.get_or_create(
                    mahasiswa=mahasiswa,
                    supervisor=current_supervisor, 
                    evaluation_form=evaluation_form,
                    defaults={'is_filled': False}
                )

                for question in questions:
                    answer_key = f'answer_{question.pk}'
                    answer_text = request.POST.get(answer_key, '').strip()

                    if not answer_text:
                        raise ValueError(f"Jawaban untuk pertanyaan ID {question.pk} harus diisi.")

                    EvaluationAnswer.objects.create(
                        evaluation=evaluation_obj,
                        question=question,
                        answer=answer_text,
                    )
                
                evaluation_obj.is_filled = True
                evaluation_obj.save()
            
            messages.success(request, f"Evaluasi untuk **{mahasiswa.user.get_full_name()}** berhasil dikirim!")
            return redirect('hp_supervisor')

        except ValueError as e:
            messages.error(request, f"Gagal mengisi evaluasi: {e}")
            return render(request, 'utsCoop/fill_evaluation.html', {'form': evaluation_form, 'mahasiswa': mahasiswa, 'questions': questions})
        except Exception as e:
            messages.error(request, f"Terjadi kesalahan saat menyimpan data: {e}")
            return render(request, 'utsCoop/fill_evaluation.html', {'form': evaluation_form, 'mahasiswa': mahasiswa, 'questions': questions})


    context = {
        'form': evaluation_form,
        'mahasiswa': mahasiswa,
        'questions': questions,
    }
    return render(request, 'utsCoop/fill_eval.html', context)

def upload_job_opportunity(request):
    if not request.user.is_authenticated or not request.user.email.startswith("admincoop"):
        messages.error(request, "Akses ditolak.")
        return redirect('hp_admin')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        links = request.POST.get('links')
        media_file = request.FILES.get('media')

        if not all([title, description, links]):
            messages.error(request, "Harap isi semua kolom wajib (Title, Description, Links).")
            return render(request, 'utsCoop/upload_job_opportunity.html')

        try:
            Job.objects.create(
                title=title,
                description=description,
                links=links,
                media=media_file
            )
            messages.success(request, f"Lowongan kerja '{title}' berhasil dipublikasikan!")
            return redirect('hp_admin')

        except Exception as e:
            messages.error(request, f"Gagal menyimpan lowongan kerja: {e}")
            return render(request, 'utsCoop/upload_job_opportunity.html')
            
    return render(request, 'utsCoop/upload_job_opportunity.html')

def weekly_report_list(request):
    if not request.user.is_authenticated or not request.user.email.startswith("admincoop"):
        messages.error(request, "Akses ditolak.")
        return redirect('hp_admin')
        
    report_sessions = WeeklyReportSession.objects.select_related(
        'mahasiswa__user'
    ).order_by('-tanggal', '-minggu_ke')
    
    context = {
        'report_sessions': report_sessions
    }
    
    return render(request, 'utsCoop/weekly_report_list.html', context)

def weekly_report_detail(request, session_id):
    if not request.user.is_authenticated or not request.user.email.startswith("admincoop"):
        messages.error(request, "Akses ditolak.")
        return redirect('hp_admin')
    session = get_object_or_404(
        WeeklyReportSession.objects.select_related('mahasiswa__user'),
        pk=session_id
    )
    
    try:
        answers = WeeklyReportAnswer.objects.get(session=session)
    except WeeklyReportAnswer.DoesNotExist:
        messages.error(request, "Jawaban laporan mingguan tidak ditemukan.")
        return redirect('weekly_report_list') 

    context = {
        'session': session,
        'mahasiswa': session.mahasiswa,
        'answers': answers,
    }
    
    return render(request, 'utsCoop/weekly_report_detail.html', context)

def final_report_list(request):
    if not request.user.is_authenticated or not request.user.email.startswith("admincoop"):
        messages.error(request, "Akses ditolak.")
        return redirect('hp_admin')
        
    final_reports = FinalReport.objects.select_related(
        'mahasiswa__user'
    ).order_by('-tanggal_upload')
    
    context = {
        'final_reports': final_reports
    }
    
    return render(request, 'utsCoop/final_report_list.html', context)

def download_final_report(request, nim):    
    if not request.user.is_authenticated or not request.user.email.startswith("admincoop"):
        raise Http404("Akses ditolak. Hanya Admin yang dapat mengunduh laporan.")
        
    try:
        final_report = FinalReport.objects.select_related('mahasiswa').get(mahasiswa__nim=nim)
        
        if not final_report.filereport:
            messages.error(request, f"File laporan untuk NIM {nim} tidak ditemukan di penyimpanan.")
            return redirect('final_report_list')

        file_handle = final_report.filereport.open()
        
        response = FileResponse(file_handle, content_type='application/pdf') 
        
        file_name = f"Final_Report_{nim}_{final_report.tanggal_upload}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        
        return response
        
    except FinalReport.DoesNotExist:
        messages.error(request, f"Laporan Akhir untuk NIM {nim} belum disubmit.")
        return redirect('final_report_list')
    except Exception as e:
        messages.error(request, f"Terjadi kesalahan saat mengunduh: {e}")
        return redirect('final_report_list')
    
def send_mail(request):
    if not request.user.is_authenticated or not request.user.email.endswith("@student.prasetiyamulya.ac.id"):
        messages.error(request, "Akses ditolak.")
        return redirect('login')

    user = request.user
    
    try:
        mahasiswa = Mahasiswa.objects.get(user=user)
    except Mahasiswa.DoesNotExist:
        mahasiswa = None

    context = {
        'mahasiswa': mahasiswa,
        'user_email': user.email
    }

    if request.method == "POST":
        subject = request.POST.get("subject", "Pesan dari Mahasiswa Co-Op")
        message_body = request.POST.get("message_body")
        
        if not message_body:
            messages.error(request, "Pesan tidak boleh kosong.")
            return render(request, 'utsCoop/send_mail.html', context) 
        
        admin_email = 'admincoop@prasetiyamulya.ac.id'
        
        full_message = (
            f"PENGIRIM: {mahasiswa.user.get_full_name()} (NIM: {mahasiswa.nim})\n"
            f"EMAIL: {user.email}\n\n"
            f"------------------------------------\n\n"
            f"{message_body}"
        )

        try:
            simulate_send_mail(subject, full_message, [admin_email])
            
            messages.success(request, "Pesan berhasil dikirim ke Admin Co-Op.")
            return redirect('hp_mahasiswa')
        
        except Exception as e:
            messages.error(request, f"Gagal mengirim pesan: {e}")
            return render(request, 'utsCoop/send_mail.html', context)

    return render(request, 'utsCoop/send_mail.html', context)

def simulate_send_mail(subject, message, recipient_list):
    """Placeholder function to simulate sending an email."""
    print(f"--- SIMULATED EMAIL SENT ---")
    print(f"Subject: {subject}")
    print(f"To: {', '.join(recipient_list)}")
    print(f"Body snippet: {message[:100]}...")
    print(f"----------------------------")
    return True 

def application_status(request):
    if not request.user.is_authenticated or not request.user.email.endswith("@student.prasetiyamulya.ac.id"):
        messages.error(request, "Akses ditolak.")
        return redirect('login')

    job_list = Job.objects.all().order_by('-job_id') 

    try:
        mahasiswa = Mahasiswa.objects.get(user=request.user)
    except Mahasiswa.DoesNotExist:
        messages.error(request, "Anda belum terdaftar.")
        return redirect('regist_coop')
    
    context = {
        'job_list': job_list,
        'mahasiswa': mahasiswa,
    }

    return render(request, 'utsCoop/application_status.html', context)

def job_application_status_list(request):
    if not request.user.is_authenticated or not request.user.email.endswith("@student.prasetiyamulya.ac.id"):
        messages.error(request, "Akses ditolak.")
        return redirect('login')

    try:
        mahasiswa = Mahasiswa.objects.get(user=request.user)
    except Mahasiswa.DoesNotExist:
        messages.error(request, "Data Co-Op Anda tidak ditemukan.")
        return redirect('regist_coop')

    applications = JobApplication.objects.filter(
        mahasiswa=mahasiswa
    ).select_related('job').order_by('-application_date')

    context = {
        'applications': applications,
    }
    
    return render(request, 'utsCoop/application_status.html', context)

def apply_to_job(request, job_id):
    if not request.user.is_authenticated or not request.user.email.endswith("@student.prasetiyamulya.ac.id"):
        messages.error(request, "Akses ditolak.")
        return redirect('login')

    if request.method != 'POST':
        return redirect('hp_mahasiswa') 

    try:
        mahasiswa = Mahasiswa.objects.get(user=request.user)
        job = get_object_or_404(Job, pk=job_id)

        JobApplication.objects.create(
            mahasiswa=mahasiswa,
            job=job,
            status=ApplicationStatus.PENDING
        )
        
        messages.success(request, f"Lamaran untuk '{job.title}' berhasil diajukan! Status Anda saat ini adalah Pending Review.")
        
    except IntegrityError:
        messages.warning(request, f"Anda sudah melamar ke '{job.title}' sebelumnya.")
        
    except Mahasiswa.DoesNotExist:
        messages.error(request, "Data Mahasiswa tidak ditemukan.")
        
    except Exception as e:
        messages.error(f"Gagal mengajukan lamaran: {e}")

    return redirect('hp_mahasiswa') 

def download_evaluation_pdf(request, evaluation_id):
    # Ambil evaluation
    evaluation = Evaluation.objects.get(id=evaluation_id)

    # Set response jadi PDF
    response = HttpResponse(content_type='application/pdf')
    filename = f"evaluation_{evaluation.mahasiswa.nim}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Buat PDF
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 100, "Evaluation Report")

    # Info Mahasiswa & Supervisor
    p.setFont("Helvetica", 12)
    p.drawString(100, height - 140, f"Mahasiswa: {evaluation.mahasiswa.user.get_full_name()}")
    p.drawString(100, height - 160, f"NIM: {evaluation.mahasiswa.nim}")
    p.drawString(100, height - 180, f"Supervisor: {evaluation.supervisor.nama}")
    p.drawString(100, height - 200, f"Perusahaan: {evaluation.supervisor.perusahaan.nama}")
    p.drawString(100, height - 220, f"Email Supervisor: {evaluation.supervisor.email}")
    p.drawString(100, height - 240, f"Status: {'Completed' if evaluation.is_filled else 'Pending'}")

    # Jawaban Evaluation
    y = height - 280
    answers = EvaluationAnswer.objects.filter(evaluation=evaluation)
    for idx, ans in enumerate(answers, start=1):
        question = ans.question.question if ans.question else "Unknown Question"
        answer = ans.answer if ans.answer else "-"
        p.drawString(100, y, f"{idx}. {question}")
        y -= 20
        p.drawString(120, y, f"Answer: {answer}")
        y -= 30
        if y < 100:  # kalau sudah mau habis halaman
            p.showPage()
            y = height - 100

    # Tutup PDF
    p.showPage()
    p.save()
    return response

def download_all_evaluations_pdf(request, evaluation_id):
    evaluation_form = get_object_or_404(EvaluationForm, id=evaluation_id)
    evaluations = Evaluation.objects.filter(evaluation_form=evaluation_form)

    # Buat response PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="evaluation_{evaluation_id}_all.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # Judul PDF
    elements.append(Paragraph(f"Evaluation Report - {evaluation_form.title}", styles['Title']))
    elements.append(Spacer(1, 12))

    # Header tabel
    data = [["NIM", "Nama Mahasiswa", "Supervisor", "Email", "Status"]]

    # Isi tabel
    for eval in evaluations:
        data.append([
            eval.mahasiswa.nim,
            eval.mahasiswa.user.get_full_name() if eval.mahasiswa and eval.mahasiswa.user else "-",
            f"{eval.supervisor.nama} ({eval.supervisor.perusahaan.nama})" if eval.supervisor and eval.supervisor.perusahaan else "-",
            eval.supervisor.email if eval.supervisor else "-",
            "Completed" if eval.is_filled else "Pending"
        ])

    # Buat tabel
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    # Build PDF
    doc.build(elements)
    return response