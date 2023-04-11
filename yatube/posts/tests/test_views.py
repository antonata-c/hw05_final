from django import forms
from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Post, Group, User, Follow
from posts.forms import PostForm


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Пользователь')
        cls.author = User.objects.create_user(username='Супер автор')
        cls.author_2 = User.objects.create_user(username='Не подписываемся')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.follow = Follow.objects.create(
            user=cls.user,
            author=cls.author
        )

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.user_client = Client()
        self.user_client.force_login(self.user)

    def context_tester(self, response, post_check=False):
        """Служебная функция для тестов контекстов"""
        if post_check:
            post = response.context.get('post')
        else:
            post = response.context.get('page_obj')[0]
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.pub_date, self.post.pub_date)
        self.assertEqual(post.image, self.post.image)

    # def count_following_posts(self):
    #     posts_count = (Post
    #                    .objects
    #                    .select_related('author', 'group')
    #                    .filter(author__following__user=self.user).count())
    #     return posts_count

    def test_index_page_has_correct_context(self):
        """Проверяем контекст главной страницы"""
        response = self.author_client.get(reverse('posts:index'))
        self.context_tester(response)

    def test_group_page_has_correct_context(self):
        """Проверяем контекст списка постов группы"""
        response = self.author_client.get(reverse('posts:group_list',
                                                  args=(self.group.slug,)))
        self.context_tester(response)

    def test_profile_page_has_correct_context(self):
        """Проверяем контекст профиля"""
        response = self.author_client.get(reverse('posts:profile', args=(
            self.author.username,)))
        self.context_tester(response)

    def test_post_detail_page_has_correct_context(self):
        """Проверяем контекст подробностей поста"""
        response = self.author_client.get(reverse('posts:post_detail',
                                                  args=(self.post.pk,)))
        self.context_tester(response, post_check=True)

    def test_create_and_edit_post_page_has_correct_context(self):
        """Проверяем контекст формы создания и редактирования постов"""
        post_page_requests = (
            ('posts:post_create', ()),
            ('posts:post_edit', (self.post.pk,))
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField,
        }
        for url, args in post_page_requests:
            with self.subTest(url=reverse(url, args=args)):
                response = self.author_client.get(reverse(url, args=args))
                self.assertIn('form', response.context)
                form = response.context.get('form')
                self.assertIsInstance(form, PostForm)
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = (response
                                      .context
                                      .get('form')
                                      .fields
                                      .get(value))
                        self.assertIsInstance(form_field, expected)

    def test_post_not_appeared_in_new_group(self):
        """Проверяем что пост появляется в нужной группе"""
        new_group = Group.objects.create(
            title="Новая группа",
            slug="new_slug",
            description="Новое описание",
        )
        response = self.author_client.get(reverse(
            'posts:group_list',
            args=(new_group.slug,)))
        self.assertEqual(len(response.context.get('page_obj')), 0)
        self.assertIsNotNone(self.post.group)
        old_group_response = self.author_client.get(reverse(
            'posts:group_list',
            args=(self.group.slug,)))
        self.assertContains(old_group_response, self.post)

    def test_authorized_client_can_follow(self):
        """Проверяет что авторизованный клиент может подписаться"""
        Follow.objects.all().delete()
        self.user_client.get(
            reverse('posts:profile_follow', args=(self.author,))
        )
        self.assertEqual(Follow.objects.all().count(), 1)
        follow = Follow.objects.first()
        self.assertEqual(follow.user, self.user)
        self.assertEqual(follow.author, self.author)

    def test_authorized_client_can_unfollow(self):
        """Проверяет что авторизованный клиент может отписаться"""
        self.assertEqual(Follow.objects.all().count(), 1)
        self.user_client.get(
            reverse('posts:profile_unfollow', args=(self.author,))
        )
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_new_post_appears_at_followed_profile(self):
        """Проверяет что пост появляется в постах подписок"""
        response = self.user_client.get(reverse('posts:follow_index'))
        self.context_tester(response)

    def test_new_posts_not_appeared_at_follows(self):
        """Проверяет что пост не появляется в постах подписок"""
        response = self.author_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context.get('page_obj')), 0)

    def test_double_follow(self):
        Follow.objects.all().delete()
        self.user_client.get(
            reverse('posts:profile_follow', args=(self.author,))
        )
        self.user_client.get(
            reverse('posts:profile_follow', args=(self.author,))
        )
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_follow_user_on_user(self):
        Follow.objects.all().delete()
        self.user_client.get(
            reverse('posts:profile_follow', args=(self.user,))
        )
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_z_cache_posts_index_page(self):
        """Проверяет кэширование главной страницы"""
        content_first = self.client.get(reverse('posts:index')).content

        self.post.delete()

        content_second = self.client.get(reverse('posts:index')).content
        self.assertEqual(content_first, content_second)

        cache.clear()

        content_last = self.client.get(reverse('posts:index')).content
        self.assertNotEqual(content_second, content_last)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='new_follower')
        cls.author = User.objects.create_user(username='new_author')
        cls.group = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_slug',
            description='Тестовое описание'
        )
        cls.follower = Follow.objects.create(
            user=cls.user,
            author=cls.author,
        )
        cls.POSTS_SHOW_REMAINING = 3
        for post_number in range(settings.POSTS_SHOW_AMOUNT
                                 + cls.POSTS_SHOW_REMAINING):
            Post.objects.create(
                text=f'Тестовый пост {post_number}',
                author=cls.author,
                group=cls.group,
            )

    def setUp(self):
        self.follower_client = Client()
        self.follower_client.force_login(self.user)

    def test_pages_contains_correct_amount_of_posts(self):
        """Проверяем что на странице правильное количество постов"""
        url_names_with_args = (
            ('posts:index', None),
            ('posts:profile', (self.author,)),
            ('posts:group_list', (self.group.slug,)),
            ('posts:follow_index', None)
        )
        pages_with_posts_amount = (
            ('?page=1', settings.POSTS_SHOW_AMOUNT),
            ('?page=2', self.POSTS_SHOW_REMAINING),
        )
        for url, args in url_names_with_args:
            with self.subTest(url=url):
                for page, posts_amount in pages_with_posts_amount:
                    with self.subTest(page=page):
                        response = self.follower_client.get(reverse(
                            url, args=args) + page)
                        self.assertEqual(len(response.context.get(
                            'page_obj')), posts_amount)
