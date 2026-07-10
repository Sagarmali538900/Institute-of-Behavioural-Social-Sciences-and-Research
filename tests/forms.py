from django import forms
from django.forms import inlineformset_factory
from .models import Exam, Section, Question, Option

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'description', 'shared_with']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter Exam Title', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'placeholder': 'Enter Exam Description...', 'rows': 4, 'class': 'form-control'}),
            'shared_with': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            self.fields.pop('shared_with', None)
        else:
            from django.contrib.auth.models import User
            self.fields['shared_with'].queryset = User.objects.filter(is_superuser=False, is_staff=False)
            self.fields['shared_with'].label = "Share with Franchise Branches"
            self.fields['shared_with'].required = False


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['name', 'description', 'duration_minutes', 'duration_seconds', 'order']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Section Name (e.g. Cognitive)', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'placeholder': 'Section Instructions...', 'rows': 2, 'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'placeholder': 'Min', 'min': 0, 'class': 'form-control'}),
            'duration_seconds': forms.NumberInput(attrs={'placeholder': 'Sec', 'min': 0, 'max': 59, 'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text', 'image', 'question_type', 'order']
        widgets = {
            'text': forms.Textarea(attrs={'placeholder': 'Enter Question text...', 'rows': 3, 'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'question_type': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class OptionForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = ['text', 'image', 'score']
        widgets = {
            'text': forms.TextInput(attrs={'placeholder': 'Option text', 'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'score': forms.NumberInput(attrs={'placeholder': 'Score/weight (e.g., 1.0 or 5.0)', 'step': '0.1', 'class': 'form-control'}),
        }

OptionFormSet = inlineformset_factory(
    Question, Option, 
    form=OptionForm, 
    extra=4, 
    can_delete=True,
    min_num=1,
    validate_min=True
)
