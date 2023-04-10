from django.test import TestCase
from django.conf import settings

from posts.models import Group, User, Post


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Супер новый классный тестовый пост',
        )

    def test_model_have_correct_object_names(self):
        """Проверяем корректность __str__ для поста"""
        post = self.post
        expected_post_str = post.text[:settings.POST_TEXT_LENGTH]
        self.assertEqual(expected_post_str, post.__str__())

    def test_group_have_correct_str_method(self):
        """Проверяем корректность __str__ для группы"""
        group = self.group
        self.assertEqual('Тестовая группа', group.__str__())

    def test_post_model_have_correct_verbose_name(self):
        """Проверяем корректность verbose_name полей group и author"""
        post = self.post
        field_verbose_names = {
            'text': 'Текст поста',
            'group': 'Группа',
            'author': 'Автор поста',
            'pub_date': 'Дата создания',
        }
        for field, expected in field_verbose_names.items():
            with self.subTest(field=field):
                self.assertEqual(post._meta.get_field(field).verbose_name,
                                 expected)

    def test_post_model_have_correct_help_text(self):
        """Проверяем корректность help_text полей group и author"""
        post = self.post
        field_verbose_names = {
            'text': 'Введите текст поста',
            'group': 'Группа, к которой будет относиться пост',
        }
        for field, expected in field_verbose_names.items():
            with self.subTest(field=field):
                self.assertEqual(post._meta.get_field(field).help_text,
                                 expected)
