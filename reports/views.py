from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db import models
from tests.models import Exam, Section, Question, Option
from candidates.models import ExamAssignment, Candidate, ExamSession, CandidateAnswer
from .models import ExamResult, SectionResult, SentEmailLog
from .forms import AssignmentForm, FranchiseForm

@login_required
def admin_dashboard(request):
    """
    Renders custom dashboard metrics. Filters stats dynamically for franchise users.
    """
    is_owner = request.user.is_superuser
    
    if is_owner:
        total_exams = Exam.objects.count()
        total_candidates = Candidate.objects.count()
        total_sessions = ExamSession.objects.count()
        completed_sessions = ExamSession.objects.filter(status='completed').count()
        avg_score = ExamResult.objects.aggregate(avg=models.Avg('overall_score_percentage'))['avg'] or 0.0
        recent_results = ExamResult.objects.all().order_by('-completed_at')[:5]
    else:
        # Franchise user - show only their candidates/sessions/results
        total_exams = Exam.objects.filter(created_by=request.user).count()
        total_candidates = Candidate.objects.filter(sessions__assignment__created_by=request.user).distinct().count()
        total_sessions = ExamSession.objects.filter(assignment__created_by=request.user).count()
        completed_sessions = ExamSession.objects.filter(assignment__created_by=request.user, status='completed').count()
        avg_score = ExamResult.objects.filter(session__assignment__created_by=request.user).aggregate(avg=models.Avg('overall_score_percentage'))['avg'] or 0.0
        recent_results = ExamResult.objects.filter(session__assignment__created_by=request.user).order_by('-completed_at')[:5]

    active_sessions = total_sessions - completed_sessions
    avg_score = round(avg_score, 1)

    return render(request, 'admin/dashboard.html', {
        'total_exams': total_exams,
        'total_candidates': total_candidates,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'active_sessions': active_sessions,
        'avg_score': avg_score,
        'recent_results': recent_results,
        'is_owner': is_owner
    })


@login_required
def admin_assignments(request):
    """
    Manages exam assignments: lists current codes/emails,
    handles batch creation form, and reassignment editing.
    """
    is_owner = request.user.is_superuser
    
    if is_owner:
        assignments = ExamAssignment.objects.all().order_by('-created_at')
    else:
        assignments = ExamAssignment.objects.filter(created_by=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        form = AssignmentForm(request.POST, user=request.user)
        if form.is_valid():
            exam = form.cleaned_data['exam']
            exam_code = form.cleaned_data['exam_code']
            emails = form.cleaned_data['assigned_emails']
            
            created_count = 0
            skipped_count = 0
            
            for email in emails:
                # Associate created_by with the active logged-in user
                obj, created = ExamAssignment.objects.get_or_create(
                    exam=exam,
                    exam_code=exam_code,
                    assigned_email=email,
                    defaults={'created_by': request.user}
                )
                if created:
                    created_count += 1
                else:
                    skipped_count += 1
                    
            msg = f"Assigned {created_count} email(s) to code '{exam_code}'."
            if skipped_count > 0:
                msg += f" ({skipped_count} already existed)."
            messages.success(request, msg)
            return redirect('admin_assignments')
    else:
        form = AssignmentForm(user=request.user)
        
    return render(request, 'admin/assignments.html', {
        'assignments': assignments,
        'form': form,
        'is_owner': is_owner
    })


@login_required
def edit_assignment(request, assignment_id):
    """
    Allows reassigning / editing a single assignment's email or code.
    """
    assignment = get_object_or_404(ExamAssignment, id=assignment_id)
    
    # Block unauthorized access by other franchise users
    if not request.user.is_superuser and assignment.created_by != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        new_code = request.POST.get('exam_code', '').strip().upper()
        new_email = request.POST.get('assigned_email', '').strip().lower()
        
        if not new_code or not new_email:
            messages.error(request, "Both exam code and email are required.")
        else:
            conflict = ExamAssignment.objects.filter(exam_code=new_code, assigned_email=new_email).exclude(id=assignment.id).exists()
            if conflict:
                messages.error(request, f"Assignment for code '{new_code}' and email '{new_email}' already exists.")
            else:
                assignment.exam_code = new_code
                assignment.assigned_email = new_email
                assignment.save()
                messages.success(request, "Assignment reassigned successfully!")
                return redirect('admin_assignments')
                
    return render(request, 'admin/edit_assignment.html', {'assignment': assignment})


@login_required
def delete_assignment(request, assignment_id):
    """
    Deletes (revokes) an assignment.
    """
    assignment = get_object_or_404(ExamAssignment, id=assignment_id)
    
    # Block unauthorized deletion
    if not request.user.is_superuser and assignment.created_by != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        code = assignment.exam_code
        email = assignment.assigned_email
        assignment.delete()
        messages.success(request, f"Revoked access for {email} to exam code {code}.")
    return redirect('admin_assignments')


@login_required
def admin_results(request):
    """
    Lists exam results. Allows searching/filtering by Candidate name, email, or exam title.
    """
    query = request.GET.get('q', '').strip()
    is_owner = request.user.is_superuser

    if is_owner:
        results = ExamResult.objects.all().order_by('-completed_at')
    else:
        results = ExamResult.objects.filter(session__assignment__created_by=request.user).order_by('-completed_at')
    
    if query:
        results = results.filter(
            models.Q(session__candidate__full_name__icontains=query) |
            models.Q(session__candidate__email__icontains=query) |
            models.Q(session__exam__title__icontains=query) |
            models.Q(session__assignment__exam_code__icontains=query)
        )
        
    return render(request, 'admin/results.html', {
        'results': results,
        'query': query,
        'is_owner': is_owner
    })


@login_required
def admin_result_detail(request, result_id):
    """
    Displays full detailed question-by-question response scorecard for a candidate's session.
    """
    result = get_object_or_404(ExamResult, id=result_id)
    session = result.session
    exam = session.exam
    
    # Block unauthorized access by other franchise users
    if not request.user.is_superuser and session.assignment.created_by != request.user:
        raise PermissionDenied

    answers = {ans.question.id: ans for ans in session.answers.all()}
    
    sheet = []
    for section in exam.sections.all():
        section_questions = []
        for q in section.questions.all():
            ans = answers.get(q.id)
            selected_opts = list(ans.selected_options.all()) if ans else []
            
            q_earned = 0.0
            if ans:
                if q.question_type == 'single_select':
                    opt = selected_opts[0] if selected_opts else None
                    if opt:
                        q_earned = opt.score
                else:
                    q_earned = sum(opt.score for opt in selected_opts)
            
            section_questions.append({
                'question': q,
                'selected_options': selected_opts,
                'q_earned': q_earned,
                'q_max': q.max_possible_score,
                'answered': ans is not None
            })
            
        sheet.append({
            'section': section,
            'questions_data': section_questions
        })

    return render(request, 'admin/result_detail.html', {
        'result': result,
        'session': session,
        'sheet': sheet
    })


@login_required
def admin_email_logs(request):
    """
    Displays log history of score report emails dispatched to candidate mail IDs.
    """
    is_owner = request.user.is_superuser
    
    if is_owner:
        logs = SentEmailLog.objects.all().order_by('-sent_at')
    else:
        # Filter email logs to only candidate/assignment emails authorized by this franchise
        candidate_emails = Candidate.objects.filter(
            sessions__assignment__created_by=request.user
        ).values_list('email', flat=True)
        assigned_emails = ExamAssignment.objects.filter(
            created_by=request.user
        ).values_list('assigned_email', flat=True)
        logs = SentEmailLog.objects.filter(
            models.Q(recipient_email__in=candidate_emails) |
            models.Q(recipient_email__in=assigned_emails)
        ).distinct().order_by('-sent_at')

    return render(request, 'admin/email_logs.html', {
        'logs': logs,
        'is_owner': is_owner
    })


@login_required
def admin_franchises(request):
    """
    Manage franchise user logs (Owner/Superuser ONLY).
    Allows creating franchises and view logs.
    """
    if not request.user.is_superuser:
        raise PermissionDenied

    franchises = User.objects.filter(is_superuser=False, is_staff=False).order_by('-date_joined')
    
    if request.method == 'POST':
        form = FranchiseForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.save()
            messages.success(request, f"Franchise user '{user.username}' created successfully!")
            return redirect('admin_franchises')
    else:
        form = FranchiseForm()

    return render(request, 'admin/franchises.html', {
        'franchises': franchises,
        'form': form
    })


@login_required
def toggle_franchise(request, user_id):
    """
    Enables/Disables (terminates/reassigns) a franchise user (Owner/Superuser ONLY).
    """
    if not request.user.is_superuser:
        raise PermissionDenied
        
    franchise = get_object_or_404(User, id=user_id, is_superuser=False, is_staff=False)
    
    if request.method == 'POST':
        franchise.is_active = not franchise.is_active
        franchise.save()
        status = "enabled" if franchise.is_active else "disabled/terminated"
        messages.success(request, f"Franchise '{franchise.username}' has been {status}.")
        
    return redirect('admin_franchises')


def custom_login(request):
    """
    Unified custom glassmorphic login view for both Admin and Franchise.
    """
    if request.user.is_authenticated:
        return redirect('admin_dashboard')
        
    error_message = None
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('admin_dashboard')
        else:
            error_message = "Invalid username or password. Please try again."
    else:
        form = AuthenticationForm()
        
    return render(request, 'admin/login.html', {
        'form': form,
        'error_message': error_message
    })


def custom_logout(request):
    """
    Unified logout view.
    """
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('login')
