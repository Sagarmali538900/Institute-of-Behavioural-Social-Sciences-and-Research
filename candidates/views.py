import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from tests.models import Exam, Section, Question, Option
from .models import ExamAssignment, Candidate, ExamSession, CandidateAnswer
from .utils import calculate_and_finalize_results, send_candidate_report_email

def exam_entry(request):
    """
    Step 1: Prompts user to enter their exam code.
    Step 2: If code exists, prompts for Name, Email, and Mobile, checking authorized emails.
    """
    exam_code = request.GET.get('code') or request.POST.get('exam_code')
    error_message = None
    step = 1
    exam = None
    
    if exam_code:
        # Check if any assignments exist for this code
        assignments = ExamAssignment.objects.filter(exam_code=exam_code)
        if not assignments.exists():
            error_message = "Invalid Exam Code. Please verify and try again."
            exam_code = None
        else:
            exam = assignments.first().exam
            step = 2

    if request.method == 'POST' and step == 2:
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        mobile_number = request.POST.get('mobile_number', '').strip()
        
        # Authenticate Email
        is_assigned = ExamAssignment.objects.filter(exam_code=exam_code, assigned_email=email).exists()
        
        if not is_assigned:
            error_message = "This email is not authorized for this Exam Code. Contact your Administrator."
        elif not full_name or not email or not mobile_number:
            error_message = "All fields are required to start the exam."
        else:
            # Authorized! Fetch or create Candidate
            candidate, _ = Candidate.objects.get_or_create(
                email=email,
                defaults={'full_name': full_name, 'mobile_number': mobile_number}
            )
            
            # Check if this candidate already completed this exam code
            existing_session = ExamSession.objects.filter(
                candidate=candidate, 
                exam=exam,
                assignment__exam_code=exam_code
            ).first()
            
            if existing_session:
                if existing_session.status == 'completed':
                    return render(request, 'candidate/entry.html', {
                        'step': 1,
                        'error_message': "You have already completed this exam. Re-taking is not allowed."
                    })
                else:
                    # Resume session
                    return redirect('exam_start', session_id=existing_session.id)
            
            # Create new session
            assignment = ExamAssignment.objects.filter(exam_code=exam_code, assigned_email=email).first()
            session = ExamSession.objects.create(
                candidate=candidate,
                assignment=assignment,
                exam=exam,
                status='in_progress'
            )
            return redirect('exam_start', session_id=session.id)

    return render(request, 'candidate/entry.html', {
        'step': step,
        'exam_code': exam_code,
        'exam': exam,
        'error_message': error_message
    })


def exam_start(request, session_id):
    """
    Renders welcome/instruction screen. Timer does NOT start until they click "Begin".
    """
    session = get_object_or_404(ExamSession, id=session_id)
    if session.is_completed:
        return redirect('exam_completed', session_id=session.id)
        
    if request.method == 'POST':
        # Initialize section and start time
        if not session.current_section:
            session.current_section = session.exam.sections.first()
        session.section_started_at = timezone.now()
        session.save()
        return redirect('exam_run', session_id=session.id)
        
    return render(request, 'candidate/instructions.html', {'session': session})


def _advance_session_section(session):
    """
    Helper function to advance to the next section or complete the exam session.
    """
    all_sections = list(session.exam.sections.all())
    if not session.current_section:
        session.current_section = all_sections[0] if all_sections else None
        session.section_started_at = timezone.now()
        session.save()
        return session.current_section
        
    try:
        current_idx = all_sections.index(session.current_section)
    except ValueError:
        current_idx = -1
        
    if current_idx + 1 < len(all_sections):
        session.current_section = all_sections[current_idx + 1]
        session.section_started_at = timezone.now()
        session.save()
        return session.current_section
    else:
        # No more sections! Complete the exam
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.current_section = None
        session.save()
        
        # Calculate & email score
        result = calculate_and_finalize_results(session)
        send_candidate_report_email(session)
        return None


def exam_run(request, session_id):
    """
    Main running examination screen. Displays active section and countdown.
    Supports auto-saving and moving between questions.
    """
    session = get_object_or_404(ExamSession, id=session_id)
    if session.is_completed:
        return redirect('exam_completed', session_id=session.id)
        
    if not session.current_section:
        first_sec = _advance_session_section(session)
        if not first_sec:
            return redirect('exam_completed', session_id=session.id)
            
    section = session.current_section
    
    # Track section duration limits on backend
    if not session.section_started_at:
        session.section_started_at = timezone.now()
        session.save()
        
    elapsed_seconds = (timezone.now() - session.section_started_at).total_seconds()
    time_left = max(0, int(section.total_duration_seconds - elapsed_seconds))
    
    # Auto-advance if time elapsed exceeds duration limit on server load
    if time_left <= 0:
        next_sec = _advance_session_section(session)
        if next_sec:
            return redirect('exam_run', session_id=session.id)
        else:
            return redirect('exam_completed', session_id=session.id)

    # Fetch questions and candidate answers
    questions = section.questions.all()
    
    # Create map of question_id -> list of selected option_ids
    saved_answers = {}
    for ans in session.answers.filter(question__section=section):
        saved_answers[ans.question.id] = list(ans.selected_options.values_list('id', flat=True))

    # Calculate section statuses and progress counts
    sections_data = []
    all_sections = session.exam.sections.all()
    answered_q_ids = set(session.answers.values_list('question_id', flat=True))
    
    current_sec_found = False
    for sec in all_sections:
        sec_questions = sec.questions.all()
        total_q = len(sec_questions)
        answered_q = sum(1 for q in sec_questions if q.id in answered_q_ids)
        
        if sec == section:
            status = 'active'
            current_sec_found = True
        elif not current_sec_found:
            status = 'completed'
        else:
            status = 'upcoming'
            
        sections_data.append({
            'id': sec.id,
            'name': sec.name,
            'total_questions': total_q,
            'answered_questions': answered_q,
            'remaining_questions': total_q - answered_q,
            'status': status
        })

    return render(request, 'candidate/exam_run.html', {
        'session': session,
        'section': section,
        'questions': questions,
        'time_left': time_left,
        'saved_answers': json.dumps(saved_answers),
        'sections_data': sections_data
    })


@csrf_exempt
def save_answers_ajax(request, session_id):
    """
    Endpoint called in background via fetch/AJAX when user clicks options.
    Auto-saves progress instantly.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)
        
    session = get_object_or_404(ExamSession, id=session_id)
    if session.is_completed:
        return JsonResponse({'status': 'error', 'message': 'Exam already completed.'}, status=403)
        
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        option_ids = data.get('option_ids', []) # List of integers
        
        question = get_object_or_404(Question, id=question_id)
        
        # Save or update candidate answer
        candidate_answer, _ = CandidateAnswer.objects.get_or_create(
            session=session,
            question=question
        )
        
        # Clear previous selection and set new selection
        candidate_answer.selected_options.clear()
        if option_ids:
            options = Option.objects.filter(id__in=option_ids, question=question)
            candidate_answer.selected_options.add(*options)
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
def submit_section_ajax(request, session_id):
    """
    Endpoint called when the user submits section manually or when section timer expires.
    Advances the exam section and returns details for page updates.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)
        
    session = get_object_or_404(ExamSession, id=session_id)
    if session.is_completed:
        return JsonResponse({'status': 'success', 'completed': True})
        
    # Save any final answers sent in the payload
    try:
        data = json.loads(request.body)
        answers = data.get('answers', {}) # Dict of {question_id: [option_ids]}
        for q_id, opt_ids in answers.items():
            question = Question.objects.filter(id=q_id).first()
            if question:
                candidate_answer, _ = CandidateAnswer.objects.get_or_create(
                    session=session,
                    question=question
                )
                candidate_answer.selected_options.clear()
                if opt_ids:
                    options = Option.objects.filter(id__in=opt_ids, question=question)
                    candidate_answer.selected_options.add(*options)
    except Exception:
        pass # Fault tolerant if payload is empty/missing
        
    # Advance
    next_sec = _advance_session_section(session)
    
    if next_sec:
        return JsonResponse({
            'status': 'success', 
            'completed': False,
            'next_url': redirect('exam_run', session_id=session.id).url
        })
    else:
        return JsonResponse({
            'status': 'success', 
            'completed': True,
            'next_url': redirect('exam_completed', session_id=session.id).url
        })


def exam_completed(request, session_id):
    """
    Score card screen presented to candidate showing metrics percentages.
    """
    session = get_object_or_404(ExamSession, id=session_id)
    if not session.is_completed:
        return redirect('exam_run', session_id=session.id)
        
    result = getattr(session, 'result', None)
    if not result:
        # Fallback in case calculation was skipped
        result = calculate_and_finalize_results(session)
        send_candidate_report_email(session)
        
    section_results = result.section_results.all()
    
    return render(request, 'candidate/completed.html', {
        'session': session,
        'result': result,
        'section_results': section_results
    })
