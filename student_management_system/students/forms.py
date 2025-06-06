from django import forms
from .models import Student, Result

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['enrollment_id', 'name', 'email', 'address', 'phone', 'date_of_birth', 'photo']
        widgets = {
            'enrollment_id': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ['student', 'semester', 'subject', 'marks', 'total_marks', 'grade', 'exam_date', 'result_file']
        widgets = {
            'student': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Select Student'
            }),
            'semester': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_semester'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_subject',
                'placeholder': 'Subject will be populated based on semester'
            }),
            'marks': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter marks obtained',
                'min': '0',
                'max': '100'
            }),
            'total_marks': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter total marks',
                'min': '1',
                'max': '100'
            }),
            'grade': forms.Select(attrs={
                'class': 'form-select',
                'readonly': 'readonly'
            }),
            'exam_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'result_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = Student.objects.all()
        self.fields['student'].empty_label = "Select Student"
        self.fields['grade'].widget.attrs['readonly'] = True