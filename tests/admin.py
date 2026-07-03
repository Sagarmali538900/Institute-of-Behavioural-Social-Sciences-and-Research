from django.contrib import admin
from .models import Exam, Section, Question, Option

class SectionInline(admin.TabularInline):
    model = Section
    extra = 1

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'created_by', 'total_sections', 'total_questions', 'created_at')
    search_fields = ('title',)
    filter_horizontal = ('shared_with',)
    inlines = [SectionInline]

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'exam', 'duration_display', 'order')
    list_filter = ('exam',)
    search_fields = ('name',)
    ordering = ('exam', 'order')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'text_snippet', 'section', 'question_type', 'order')
    list_filter = ('section__exam', 'section', 'question_type')
    search_fields = ('text',)
    inlines = [OptionInline]
    ordering = ('section', 'order')

    def text_snippet(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_snippet.short_description = 'Question Text'

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'question', 'score')
    list_filter = ('question__section__exam', 'question')
    search_fields = ('text',)
