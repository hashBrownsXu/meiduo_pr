from .models import User
import re
from django.contrib.auth.backends import ModelBackend


def get_uer_by_account(account):
    """
       根据account查询用户
       :param account: 用户名或者手机号
       :return: user
       """
    try:
        if re.match(r'^1[3-9]\d{9}', account):
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user


class UsernameMobileAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        :param request:
        :param username:
        :param password:
        :param kwargs:
        :return:
        """

        # 根据传入的username或者mobile获取user对象
        user = get_uer_by_account(username)

        # 检验用户是否存在，和检验密码是否正确
        if user and user.check_password(password):
            return user

