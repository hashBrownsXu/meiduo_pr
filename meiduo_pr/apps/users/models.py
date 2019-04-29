from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    mobile = models.CharField(max_length=20, unique=True, verbose_name='手机号')
    # 如果给已经存在的模型加入字段的时候，必须给默认值，或者可以设置为空
    email_active = models.BooleanField(default=False, verbose_name='邮箱验证状态')

    class Meta:
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username

# Create your models here.
