from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import models

User = get_user_model()


class PubDateModel(models.Model):
    """Абстрактная модель. Добавляет дату создания."""

    pub_date = models.DateTimeField('Дата создания',
                                    auto_now_add=True)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        help_text='Пользователь'
    )
    text = models.TextField('Текст',
                            help_text='Введите текст')

    class Meta:
        ordering = ('-pub_date',)
        abstract = True

    def __str__(self):
        return self.text[:settings.POSTS_TEXT_LENGTH]