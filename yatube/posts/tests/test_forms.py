import shutil
import tempfile
from http import HTTPStatus

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from posts.forms import PostForm, CommentForm
from posts.models import Post, User, Group, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост_',
            group=cls.group,
            author=cls.user,
        )
        cls.image = SimpleUploadedFile(
            name='small.png',
            content=small_gif,
            content_type='posts/small.png'
        )
        cls.form = PostForm

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_new_post_added(self):
        """Проверяет что после отправки формы создается пост"""
        Post.objects.all().delete()
        form_data = {
            'text': self.post.text,
            'group': self.group.pk,
            'image': self.image,
        }
        prev_posts_count = Post.objects.count()
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), prev_posts_count + 1)
        post = Post.objects.first()
        file = post.image.file
        self.assertEqual(file.read(), small_gif)
        file.close()
        self.assertEqual(post.text, form_data.get('text'))
        self.assertEqual(post.group.pk, form_data.get('group'))
        self.assertEqual(post.author, self.user)

    def test_base_changed(self):
        """Проверяет что после отправки формы редактируется пост"""
        new_group = Group.objects.create(
            title='Новая группа',
            slug='new_slug',
            description='Новое описание'
        )
        form_data = {
            'text': 'Отредачили старый пост',
            'group': new_group.pk,
        }
        self.authorized_client.post(
            reverse('posts:post_edit', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        post = Post.objects.first()
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group.pk, form_data.get('group'))
        self.assertEqual(post.text, form_data.get('text'))
        response = self.authorized_client.get(reverse(
            'posts:group_list',
            args=(self.group.slug,)))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.context.get('page_obj')), 0)

    def test_guest_cant_post(self):
        """Проверяет что пользователь не может добавлять посты"""
        form_data = {
            'text': 'Супер новый пост который не отправится',
            'group': self.group.pk,
        }
        prev_posts_amount = Post.objects.count()
        self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        new_posts_amount = Post.objects.count()
        self.assertEqual(prev_posts_amount, new_posts_amount)


class CommentFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост_',
            group=cls.group,
            author=cls.user,
        )
        cls.form = CommentForm

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_authorized_can_add_comments(self):
        """Проверяет что авторизованный пользователь
        может оставить комментарий"""
        Comment.objects.all().delete()
        form_data = {
            'text': 'Крутой комментарий!',
        }
        prev_comments_count = Comment.objects.count()
        self.authorized_client.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), prev_comments_count + 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.text, form_data.get('text'))
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.author, self.user)

    def test_guest_can_not_add_comments(self):
        """Проверяет что гостевой пользователь
        не может добавлять комментарии"""
        form_data = {
            'text': 'Крутой комментарий 2!',
        }
        prev_comments_count = Comment.objects.count()
        self.client.post(
            reverse('posts:add_comment', args=(self.post.pk,)),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), prev_comments_count)
