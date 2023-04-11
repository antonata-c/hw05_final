from http import HTTPStatus

from django.test import TestCase, Client
from django.urls import reverse

from posts.models import Post, Group, User, Follow


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.user = User.objects.create_user(username='test')
        cls.following_author = User.objects.create_user(username='following')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
            group=cls.group,
        )
        cls.reverse_url_names = (
            ('posts:index', None, '/'),
            ('posts:group_list', (cls.group.slug,),
             f'/group/{cls.group.slug}/'),
            ('posts:post_detail', (cls.post.pk,),
             f'/posts/{cls.post.pk}/'),
            ('posts:profile', (cls.author,),
             f'/profile/{cls.author}/'),
            ('posts:post_create', None,
             '/create/'),
            ('posts:post_edit', (cls.post.pk,),
             f'/posts/{cls.post.pk}/edit/'),
            ('posts:add_comment', (cls.post.pk,),
             f'/posts/{cls.post.pk}/comment/'),
            ('posts:profile_follow', (cls.following_author,),
             f'/profile/{cls.following_author}/follow/'),
            ('posts:profile_unfollow', (cls.following_author,),
             f'/profile/{cls.following_author}/unfollow/'),
            ('posts:follow_index', None,
             f'/follow/')
        )
        cls.redirects = (
            'posts:profile_follow',
            'posts:profile_unfollow',
            'posts:add_comment',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_reverse_returns_correct_urls(self):
        """Проверяем что reverse() возвращает корректные urls"""
        for name, args, url in self.reverse_url_names:
            with self.subTest(address=reverse(name, args=args)):
                self.assertEqual(reverse(name, args=args), url)

    def test_urls_uses_correct_templates(self):
        """Проверяем views перенаправляет на корректные шаблоны"""
        template_url_names = (
            ('posts:index', None,
             'posts/index.html'),
            ('posts:group_list', (self.group.slug,),
             'posts/group_list.html'),
            ('posts:post_detail', (self.post.pk,),
             'posts/post_detail.html'),
            ('posts:profile', (self.author,),
             'posts/profile.html'),
            ('posts:post_create', None,
             'posts/post_create_and_edit.html'),
            ('posts:post_edit', (self.post.pk,),
             'posts/post_create_and_edit.html'),
            ('posts:follow_index', None,
             'posts/follow.html'),
        )
        for name, args, template in template_url_names:
            with self.subTest(address=reverse(name, args=args)):
                response = self.author_client.get(reverse(name, args=args))
                self.assertTemplateUsed(response, template)

    def test_urls_access_for_author_client(self):
        """Проверяем доступ автора"""
        for name, args, template in self.reverse_url_names:
            with self.subTest(address=reverse(name, args=args)):
                response = self.author_client.get(reverse(name, args=args))
                if name in self.redirects:
                    self.assertEqual(response.status_code, HTTPStatus.FOUND)
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_access_for_authorized_client(self):
        """Проверяем доступ клиента вошедшего в аккаунт"""
        for name, args, template in self.reverse_url_names:
            with self.subTest(address=reverse(name, args=args)):
                response = self.authorized_client.get(reverse(
                    name, args=args))
                if name == 'posts:post_edit':
                    self.assertRedirects(response, reverse(
                        'posts:post_detail', args=args))
                elif name in self.redirects:
                    self.assertEqual(response.status_code, HTTPStatus.FOUND)
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_access_for_anonymous_client(self):
        """Проверяем доступ клиента не вошедшего в аккаунт"""
        login_reverse = reverse('users:login')
        anonymous_redirects = ('posts:post_edit',
                               'posts:post_create',
                               'posts:add_comment',
                               'posts:profile_follow',
                               'posts:profile_unfollow',
                               'posts:follow_index')
        for name, args, template in self.reverse_url_names:
            reverse_name = reverse(name, args=args)
            with self.subTest(address=reverse_name):
                response = self.client.get(reverse_name)
                if name in anonymous_redirects:
                    self.assertRedirects(
                        response,
                        f'{login_reverse}?next={reverse_name}'
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_errors_uses_custom_template_and_get_404(self):
        """Проверяет что несуществующий url вернет код 404 и
        направит на кастомный шаблон ошибки"""
        response = self.authorized_client.get('/unexistent/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
