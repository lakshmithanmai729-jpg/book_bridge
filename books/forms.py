from django import forms
from .models import Book


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            'title', 'author', 'category', 'description', 'price', 'condition',
            'location_city', 'location_area', 'pincode', 'contact_phone', 'image'
        ]
        widgets = {
            'location_city': forms.TextInput(attrs={'placeholder': 'e.g. Hyderabad'}),
            'location_area': forms.TextInput(attrs={'placeholder': 'e.g. Madhapur, JNTU Campus'}),
            'pincode': forms.TextInput(attrs={'placeholder': 'e.g. 500085'}),
            'contact_phone': forms.TextInput(attrs={'placeholder': 'e.g. 9876543210 (WhatsApp preferred)'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Image file should be smaller than 5MB.')
        return image