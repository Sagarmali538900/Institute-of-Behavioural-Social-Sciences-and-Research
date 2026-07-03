from django.contrib import admin
from .models import ExamResult, SectionResult, SentEmailLog

class SectionResultInline(admin.TabularInline):
    model = SectionResult
    extra = 0
    readonly_fields = ('section', 'score_percentage')

@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'overall_score_percentage', 'completed_at')
    search_fields = ('session__candidate__full_name', 'session__candidate__email')
    inlines = [SectionResultInline]

@admin.register(SectionResult)
class SectionResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'exam_result', 'section', 'score_percentage')
    list_filter = ('section',)

@admin.register(SentEmailLog)
class SentEmailLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient_email', 'subject', 'sent_at', 'status')
    search_fields = ('recipient_email', 'subject')
    list_filter = ('status',)
