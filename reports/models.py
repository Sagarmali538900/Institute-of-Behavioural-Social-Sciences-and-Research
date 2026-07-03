from django.db import models

class ExamResult(models.Model):
    session = models.OneToOneField('candidates.ExamSession', on_delete=models.CASCADE, related_name='result')
    overall_score_percentage = models.FloatField(default=0.0)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result: {self.session.candidate.full_name} - {self.overall_score_percentage}%"


class SectionResult(models.Model):
    exam_result = models.ForeignKey(ExamResult, on_delete=models.CASCADE, related_name='section_results')
    section = models.ForeignKey('tests.Section', on_delete=models.CASCADE)
    score_percentage = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.exam_result} | {self.section.name}: {self.score_percentage}%"


class SentEmailLog(models.Model):
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255, default='Sent')

    def __str__(self):
        return f"Email to {self.recipient_email} - {self.status} at {self.sent_at}"
