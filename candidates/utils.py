from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from reports.models import ExamResult, SectionResult, SentEmailLog
from tests.models import Section

def calculate_and_finalize_results(session):
    """
    Calculates the exam scores: section-wise percentages and overall percentage.
    Saves the metrics in ExamResult and SectionResult tables.
    Returns the generated ExamResult object.
    """
    # Prevent recalculating if result already exists
    if hasattr(session, 'result'):
        return session.result

    exam = session.exam
    sections = exam.sections.all()
    
    total_earned_score = 0.0
    total_max_score = 0.0
    
    section_scores = [] # List of tuples: (Section, earned, max)
    
    for section in sections:
        questions = section.questions.all()
        section_earned = 0.0
        section_max = 0.0
        
        for question in questions:
            # Max possible score for this question
            q_max = question.max_possible_score
            section_max += q_max
            
            # Earned score from candidate's answer
            ans = session.answers.filter(question=question).first()
            if ans:
                if question.question_type == 'single_select':
                    # Single choice: get the score of the selected option
                    opt = ans.selected_options.first()
                    if opt:
                        section_earned += opt.score
                else:
                    # Multi select: sum of all selected option scores
                    for opt in ans.selected_options.all():
                        section_earned += opt.score
        
        section_scores.append((section, section_earned, section_max))
        total_earned_score += section_earned
        total_max_score += section_max

    # Compute overall percentage
    overall_percentage = 0.0
    if total_max_score > 0:
        overall_percentage = round((total_earned_score / total_max_score) * 100, 2)
        
    # Save ExamResult
    result = ExamResult.objects.create(
        session=session,
        overall_score_percentage=overall_percentage,
        completed_at=timezone.now()
    )
    
    # Save SectionResults
    for section, earned, max_val in section_scores:
        sec_percentage = 0.0
        if max_val > 0:
            sec_percentage = round((earned / max_val) * 100, 2)
        SectionResult.objects.create(
            exam_result=result,
            section=section,
            score_percentage=sec_percentage
        )
        
    return result

def send_candidate_report_email(session):
    """
    Compiles results report and sends it to candidate's email.
    Logs the email transaction in SentEmailLog.
    """
    result = session.result
    candidate = session.candidate
    exam = session.exam
    
    subject = f"Your Psychological Assessment Result: {exam.title}"
    
    # Generate content
    body = f"Hello {candidate.full_name},\n\n"
    body += f"Thank you for completing the '{exam.title}' on our portal.\n\n"
    body += f"--- ASSESSMENT RESULTS ---\n"
    body += f"Overall Score: {result.overall_score_percentage}%\n\n"
    body += f"Section-wise breakdown:\n"
    
    for sec_res in result.section_results.all():
        body += f"- {sec_res.section.name}: {sec_res.score_percentage}%\n"
        
    body += f"\nThank you,\nIBSSR Examination Team\n"
    
    # Attempt sending mail
    status = 'Sent (Mocked)'
    try:
        # Django's send_mail will write to console based on settings.py EMAIL_BACKEND
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [candidate.email],
            fail_silently=False,
        )
        status = 'Sent'
    except Exception as e:
        status = f'Failed: {str(e)}'
        
    # Log to SentEmailLog database table
    SentEmailLog.objects.create(
        recipient_email=candidate.email,
        subject=subject,
        body=body,
        status=status
    )
