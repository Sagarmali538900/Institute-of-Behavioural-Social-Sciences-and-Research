from django.db import models

class ExamAssignment(models.Model):
    exam = models.ForeignKey('tests.Exam', on_delete=models.CASCADE, related_name='assignments')
    exam_code = models.CharField(max_length=50, help_text="Access code for the exam")
    assigned_email = models.EmailField(help_text="Email address authorized to use this exam code")
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam_code', 'assigned_email')

    def __str__(self):
        return f"{self.exam_code} -> {self.assigned_email} ({self.exam.title})"


class Candidate(models.Model):
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    mobile_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class ExamSession(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='sessions')
    assignment = models.ForeignKey(ExamAssignment, on_delete=models.SET_NULL, null=True, related_name='sessions')
    exam = models.ForeignKey('tests.Exam', on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    current_section = models.ForeignKey('tests.Section', on_delete=models.SET_NULL, null=True, blank=True)
    section_started_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')

    def __str__(self):
        return f"Session: {self.candidate.full_name} - {self.exam.title} ({self.status})"
        
    @property
    def is_completed(self):
        return self.status == 'completed'


class CandidateAnswer(models.Model):
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey('tests.Question', on_delete=models.CASCADE, related_name='candidate_answers')
    selected_options = models.ManyToManyField('tests.Option')
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session', 'question')

    def __str__(self):
        return f"Ans: {self.session.id} - Q: {self.question.id}"
