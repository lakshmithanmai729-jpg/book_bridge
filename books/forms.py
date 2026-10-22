from django import forms

from .images import MAX_UPLOAD_BYTES
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
        if image and getattr(image, 'size', 0) > MAX_UPLOAD_BYTES:
            raise forms.ValidationError('Photo is too large. Please use a photo smaller than 8 MB.')
        if image and hasattr(image, 'content_type'):
            if not str(image.content_type).startswith('image/'):
                raise forms.ValidationError('Please upload an image file (JPG, PNG or WebP).')
        return image