from django.db import models


class PubDateModel(models.Model):
    """Абстрактная модель. Добавляет дату создания."""

    pub_date = models.DateTimeField('Дата создания',
                                    auto_now_add=True)

    class Meta:
        abstract = True
