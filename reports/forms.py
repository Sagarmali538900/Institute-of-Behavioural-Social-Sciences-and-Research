import uuid
from django import forms
from tests.models import Exam


class AssignmentForm(forms.Form):
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.none(),  # Will be dynamically populated
        empty_label="Select Exam",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    exam_code = forms.CharField(
        required=False,
        max_length=50,
        help_text="Leave blank to automatically generate a code.",
        widget=forms.TextInput(attrs={'placeholder': 'Leave blank to generate', 'class': 'form-control'})
    )
    assigned_emails = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Enter email addresses (one per line or comma-separated)', 
            'rows': 4, 
            'class': 'form-control'
        }),
        help_text="Authorized emails that can log in using this exam code."
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            if user.is_superuser:
                self.fields['exam'].queryset = Exam.objects.all()
            else:
                self.fields['exam'].queryset = Exam.objects.filter(created_by=user)

    def clean_exam_code(self):
        code = self.cleaned_data.get('exam_code')
        if not code:
            # Generate random 8-character code
            code = f"EXAM-{uuid.uuid4().hex[:8].upper()}"
        else:
            code = code.strip().upper()
        return code

    def clean_assigned_emails(self):
        emails_text = self.cleaned_data.get('assigned_emails', '')
        # Split by comma or newline
        raw_emails = emails_text.replace(',', '\n').split('\n')
        emails = []
        for email in raw_emails:
            email = email.strip().lower()
            if email:
                # Basic email format check
                if '@' not in email:
                    raise forms.ValidationError(f"Invalid email address: '{email}'")
                emails.append(email)
        
        if not emails:
            raise forms.ValidationError("Please enter at least one email address.")
        return emails


from django.contrib.auth.models import User

class FranchiseForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter Password', 'class': 'form-control'}),
        help_text="Password must be secure."
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Enter Username (e.g. franchise_east)', 'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter Email', 'class': 'form-control'}),
        }
        
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username
