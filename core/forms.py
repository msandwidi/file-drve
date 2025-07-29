from django import forms
from .models import ContactMessage

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border focus:outline-none',
                'placeholder': 'Votre nom complet',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border focus:outline-none',
                'placeholder': 'Votre adresse e-mail',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border focus:outline-none',
                'placeholder': 'Sujet du message',
            }),
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border focus:outline-none', 
                'rows': 5,
                'placeholder': 'Votre message',
            }),
        }
        