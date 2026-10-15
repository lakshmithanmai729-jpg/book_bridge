from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from django.contrib.auth import get_user_model

from .models import Book, BookImage, Category


class BookImageModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='seller', password='secret123')
        self.category = Category.objects.create(name='Fiction')

    def test_book_can_have_multiple_images(self):
        book = Book.objects.create(
            seller=self.user,
            category=self.category,
            title='Sample Book',
            author='Author',
            price=150,
        )

        first = SimpleUploadedFile('first.jpg', b'file-content-1', content_type='image/jpeg')
        second = SimpleUploadedFile('second.jpg', b'file-content-2', content_type='image/jpeg')

        BookImage.objects.create(book=book, image=first)
        BookImage.objects.create(book=book, image=second)

        self.assertEqual(book.images.count(), 2)
        self.assertTrue(book.gallery_images.exists())
