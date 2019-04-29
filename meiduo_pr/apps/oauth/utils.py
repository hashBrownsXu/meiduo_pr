from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings

def generate_eccess_token(openid):
    """
    签名openid
    :param openid: 用户的openid
    :return: access_token
    # serializer = Serializer(秘钥, 有效期秒)
    serializer = Serializer(settings.SECRET_KEY, 300)
    # serializer.dumps(数据), 返回bytes类型
    token = serializer.dumps({'mobile': '18512345678'})
    token = token.decode()
    """
    serializer = Serializer(settings.SECRET_KEY, expires_in=constants.ACCESS_TOKEN_EXPIRES)
    data = {'openid': openid}
    token = serializer.dumps(data)
    return token.decode()

    # 检验token
    # 验证失败，会抛出itsdangerous.BadData异常
    serializer = Serializer(settings.SECRET_KEY, 6300)
    try:
        data = serializer.loads(token)
    except BadData:
        return None