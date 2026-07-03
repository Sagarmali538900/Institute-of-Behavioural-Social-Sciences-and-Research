from django.contrib import admin
from .models import ExamAssignment, Candidate, ExamSession, CandidateAnswer

@admin.register(ExamAssignment)
class ExamAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'exam_code', 'assigned_email', 'exam', 'created_at')
    search_fields = ('exam_code', 'assigned_email')
    list_filter = ('exam',)

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'email', 'mobile_number', 'created_at')
    search_fields = ('full_name', 'email', 'mobile_number')

class CandidateAnswerInline(admin.TabularInline):
    model = CandidateAnswer
    extra = 0
    readonly_fields = ('question', 'selected_options')

@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate', 'exam', 'started_at', 'completed_at', 'current_section', 'status')
    list_filter = ('exam', 'status')
    search_fields = ('candidate__full_name', 'candidate__email')
    inlines = [CandidateAnswerInline]

@admin.register(CandidateAnswer)
class CandidateAnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'question', 'answered_at')
    list_filter = ('session__exam', 'session')
