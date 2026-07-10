from django.db import models

class Exam(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_exams')
    shared_with = models.ManyToManyField('auth.User', blank=True, related_name='shared_exams', help_text="Franchises allowed to use this exam")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def total_sections(self):
        return self.sections.count()

    @property
    def total_questions(self):
        return sum(section.questions.count() for section in self.sections.all())


class Section(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    duration_minutes = models.IntegerField(default=10, help_text="Duration minutes part")
    duration_seconds = models.IntegerField(default=0, help_text="Duration seconds part")
    order = models.IntegerField(default=0, help_text="Display order of this section")

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.exam.title} - {self.name}"

    @property
    def total_duration_seconds(self):
        return (self.duration_minutes * 60) + self.duration_seconds

    @property
    def duration_display(self):
        return f"{self.duration_minutes}m {self.duration_seconds}s"


class Question(models.Model):
    QUESTION_TYPES = [
        ('single_select', 'Single Select (Radio Buttons)'),
        ('multi_select', 'Multi Select (Checkboxes)'),
    ]
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    image = models.FileField(upload_to='question_images/', blank=True, null=True, help_text="Optional question image")
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='single_select')
    order = models.IntegerField(default=0, help_text="Display order of this question")

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Q: {self.text[:50]}..."

    @property
    def max_possible_score(self):
        """
        Calculates max possible score for this question.
        For single select, it's the maximum score of any option.
        For multi select, it's the sum of all options with positive scores.
        """
        options = list(self.options.all())
        if not options:
            return 0.0
        if self.question_type == 'single_select':
            return max(opt.score for opt in options)
        else:
            return sum(opt.score for opt in options if opt.score > 0)


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=500)
    image = models.FileField(upload_to='option_images/', blank=True, null=True, help_text="Optional choice image")
    score = models.FloatField(default=0.0, help_text="Score weight/points for selecting this option")

    def __str__(self):
        return f"{self.question.id} - {self.text[:30]}"
