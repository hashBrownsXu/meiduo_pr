from django.views import View
from django_redis import get_redis_connection
from django import http
from meiduo_pr.libs.captcha.captcha import captcha
import logging
from .constants import *
from meiduo_pr.utils.response_code import *
import random
from celery_tasks.sms.tasks import send_sms_code


logger = logging.getLogger('django')
# Create your views here.


class ImageCodeView(View):
    """生成图形验证码"""
    def get(self, request, uuid):
        """
        :param uuid: 唯一标识,用来区分当前的图形验证码属于那个用户
        :return: image
        """
        # 利用SDK 生成图形验证码 (唯一标识字符串, 图形验证内容字符串, 二进制图片数据)
        name, text, image = captcha.generate_captcha()

        # 创建redis连接对象
        redis_conn = get_redis_connection('verify_code')
        # 将图形验证码字符串存入到reids
        redis_conn.setex('img_%s' % uuid, IMAGE_CODE_REDIS_EXPIRES, text)
        print("----------------------------")
        print(text)
        # 把生成好的图片响应给前端
        return http.HttpResponse(image, content_type='image/png')


class SMSCodeView(View):
    """生成短信验证码"""
    def get(self, request, mobile):
        """

        :param request:
        :param mobile: 要接受短信验证码的手机号
        :return:
        """
        # 接收到前端 传入的 mobile, image_code, uuid
        # 创建redis连接对象 根据uuid作为key 获取到reids中当前用户的图形验证值
        # 判断用户写的图形验证码和我们redis存的是否一致
        # 发送短信
        # 将生成好的短信验证码也存储到redis,以备后期校验
        # 响应

        # 接收参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('uuid')

        # 校验参数
        if not all([image_code_client, uuid]):
            return http.JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必传参数'})

        # 创建连接到redis的对象
        redis_conn = get_redis_connection('verify_code')
        # 提取图形验证码
        image_code_server = redis_conn.get('img_%s' % uuid)

        """
        不用写这么麻烦，可以按照老师的简洁点
        if image_code_server is None:
            # 图形验证码过期或者不存在
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码失效'})
        # 删除图形验证码，避免恶意测试图形验证码
        try:
            redis_conn.delete('img_%s' % uuid)
        except Exception as e:
            logger.error(e)
        # 对比图形验证码
        image_code_server = image_code_server.decode()  # bytes转字符串
        if image_code_client.lower() != image_code_server.lower():  # 转小写后比较
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '输入图形验证码有误'})
        """
        # 删除图形验证码，让它只能用一次，防止刷
        redis_conn.delete('img_%s' % uuid)
        # 从redis中取出来的数据都是bytes类型
        # 判断用户写的图形验证码和我们redis存的是否一致:先判断是不是空的在判断前段传来的是否与后台生成的一样
        if image_code_server is None or image_code_client.lower() != image_code_server.decode().lower():
            return http.JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码错误'})

        # 生成短信验证码：生成6位数验证码
        sms_code = '%06d' % random.randint(0, 999999)
        logger.info(sms_code)

        # 创建管道对象
        pl = redis_conn.pipeline()

        #  将生成好的短信验证码也存储到redis中
        # redis_conn.setex('sms_%s' % mobile, SMS_CODE_REDIS_EXPIRES, sms_code)改成管道
        pl.setex('sms_%s' % mobile, SMS_CODE_REDIS_EXPIRES, sms_code)
        # 注意：一定要执行管道
        pl.execute()


        # 发送短信验证码
        # sms.CCP().send_template_sms(mobile, [sms_code, SMS_CODE_REDIS_EXPIRES // 60],
        #                             SEND_SMS_TEMPLATE_ID)
        # 这里的send先不执行，等到后面异步做好以后在执行


        send_sms_code.delay(mobile, sms_code)

        # 响应结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '发送短信成功'})


