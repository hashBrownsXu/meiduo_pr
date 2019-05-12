from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django import http
from django.db import DatabaseError
from django.contrib.auth import login, logout
from django.contrib.auth import authenticate, mixins
from .utils import generate_verify_email_url, check_verify_email_token

from celery_tasks.email.tasks import send_verify_email
from .models import User, Address
from meiduo_pr.utils.response_code import RETCODE
from meiduo_pr.utils.views import LoginRequiredView
from verifications.views import get_redis_connection


import re
import json
import logging

logger = logging.getLogger('django')


class RegisterView(View):
    # def post(self, request):
    #     '''实现用户注册功能'''
    #     # 接受用户表单数据：
    #     QueryDict =
    #     return render(request, )
    def get(self, request):
        return render(request, 'register.html')

    # 接受前端的数据

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code = request.POST.get('sms_code')

        # 检验判断

        allow = request.POST.get('allow')  # 单选框如果点上，就是‘on’不然就是None

        # 校验数据是否齐全

        if all([username, password, password2, mobile, sms_code, allow]) is False:
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入正确的用户名')
        # 还要输入三次，直接复制前面的改一改，正则表达式可以去js文件里面找一样的复制过来
        if not re.match(r'[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入正确的密码')
        # password两次输入的要判断是否一样，不需要使用正则表达式。
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        if not re.match(r'1[3-9]\d{9}', mobile):
            return http.HttpResponseForbidden('电话号码格式不正确，请输入正确的电话号码')
        # if not re.match(r'', sms_code):
            # reture http.HttpResponseForbidden('电子邮箱格式不正确，请输入正确的电子邮箱地址')
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        # TODO： 短信验证
        # 获取redis中的verify_code数据（就是短信验证码）
        redis_conn = get_redis_connection('verify_code')

        # 获取redis中的响应
        sms_code_server = redis_conn.get('sms_ %s' % mobile)

        # 先判断验证码是不是为空，在判断
        if sms_code_server is None or sms_code != sms_code_server.decode():
            return http.HttpResponseForbidden('短信验证码有误')

        '''
        创建user
        使用 User.objects.create_user()可以直接创建用户
        而且使用这个方法可以自动的为password加密（具体可以看手册）
        出错需要处理 导入databaseError基类(数据库稳如狗，一般不会错)
        '''
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError as e:
            # 出错信息记录到log中
            logger.error(e)
            # 出错信息需要渲染到页面
            # 使用vue渲染不会刷新页面
            return render(request, 'register.html', {'register_errmsg': '用户注册失败'})

        # 保持状态
        # 需要导入login包,位置在django.contrib.auth.__init__.py中
        login(request, user, backend=None)  # 拿到请求对象，存储用户id到session，记录他的登陆状态，来跟session里面的对比

        # 注册成功重定向到首页
        # 直接重定向 / 的话会报错，/ 是返回的是工程的注册界面（it work）但是加了view视图以后返回的是404，所以需要重定向别的
        return redirect('/')
        #
        # """
        #  """
        # 解决办法：创建一个新的应用contents,在里面的view里面重定向的页面
        # 当然这里需要加入路由地址
        # index.html使用老师给出的写死了的页面，不使用static里面做好的，一位内做好的那个index.html页面需要传入content参数，而在这里还没有给出数据，所以使用老师给出的写死的先


class UsernameCountView(View):

    def get(self, request, username):
        # 查询当前用户名的个数要么0要么1 1代表重复
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({'count': count, 'code': RETCODE.OK, 'errmsg': 'OK'})


class MobileCountView(View):

    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({'count': count, 'code': RETCODE.OK, 'errmsg': 'OK'})


class LoginView(View):

    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        # 获取传来的参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')

        # 检验是否全部参数齐全
        if not all([username, password]):
            return http.HttpResponseForbidden('缺少必传参数')

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入正确的用户名或手机号')

            # 判断密码是否是8-20个数字
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码最少8位，最长20位')

        # 验证登陆状态
        user = authenticate(username=username, password=password)
        if user is None:
            return render(request, 'login.html', {'account_errmsg': '用户名或密码错误'})

        # 实现状态保持
        login(request, user)
        # 设置状态保持的周期
        if remembered != 'on':
            # 没有记住用户：浏览器会话结束就过期
            request.session.set_expiry(0)
        else:
            # 记住用户：None表示两周后过期
            request.session.set_expiry(None)

        response = redirect(request.GET.get('next', '/'))
        response.set_cookie('username', user.username, max_age=60 * 60)
        # 响应登录结果
        # return redirect(reverse('contents:index'))
        return response


class LogoutView(View):
    '''退出登陆'''

    def get(self, request):
        # 1. 清除session中的状态信息
        logout(request)
        # login(request, user)存入的时候要传入user，会把user的id存储到session中，logout的话就直接会从request对象中找到id清除session

        # 2. 清除cookie中的username
        response = redirect(request.GET.get('next', '/'))
        response.delete_cookie('username')

        # 3. 重定向
        return response


# class UserInfoView(View):
#     def get(self, request):
#         '''提供用户中心界面'''
#         # 判断是否登陆，登陆了就返回用户中心，没有就返回登陆界面
#         # user = request.user  # 通过请求对象获取user（从session里面找）
#         # 使用 is_authenticated 方法，如果是匿名用户就返回false，
#         # 用户存在就返回true
#         # if user.is_authenticated:
#         #     return render(request, 'user_center_info.html')
#         # else:
#         #     return render(request, '/login/?next=/info/')
#         return render(request, 'user_center_info.html')
#     # return render(request, 'XXXX.html')
#

class UserInfoView(View):
    """用户中心"""

    def get(self, request):
        """提供个人信息界面"""
        context = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }
        return render(request, 'user_center_info.html', context=context)


class EmailView(View):
    """添加邮箱"""

    def put(self, request):
        """实现添加邮箱逻辑"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        email = json_dict.get('email')

        # 校验参数
        if not email:
            return http.HttpResponseForbidden('缺少email参数')
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('参数email有误')

        # 赋值email字段
        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '添加邮箱失败'})

        if not request.user.is_authenticated():
            return http.JsonResponse({'code': RETCODE.SESSIONERR, 'errmsg': '用户未登录'})

        # 异步（使用celery）发送验证邮件
        verify_url = generate_verify_email_url(request.user)
        send_verify_email.delay(email, verify_url)
        # 响应添加邮箱结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加邮箱成功'})


class VerifyEmailView(View):
    """验证邮箱"""

    def get(self, request):
        """实现邮箱验证逻辑"""
        # 接收参数
        token = request.GET.get('token')

        # 校验参数：判断token是否为空和过期，提取user
        if not token:
            return http.HttpResponseBadRequest('缺少token')

        user = check_verify_email_token(token)
        if not user:
            return http.HttpResponseForbidden('无效的token')

        # 修改email_active的值为True
        try:
            user.email_active = True
            user.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('激活邮件失败')

        # 返回邮箱验证结果
        return redirect(reverse('users:info'))


class AddressView(LoginRequiredView):
    def get(self, request):
        """提供用户收货地址界面"""
        # 获取当前用户的所有收货地址
        user = request.user
        # address = user.addresses.filter(is_deleted=False)  # 获取当前用户的所有收货地址
        address_qs = Address.objects.filter(is_deleted=False, user=user)  # 获取当前用户的所有收货地址

        address_list = []
        for address in address_qs:
            address_dict = {
                'id': address.id,
                'title': address.title,
                'receiver': address.receiver,
                'province_id': address.province_id,
                'province': address.province.name,
                'city_id': address.city_id,
                'city': address.city.name,
                'district_id': address.district_id,
                'district': address.district.name,
                'place': address.place,
                'mobile': address.mobile,
                'tel': address.tel,
                'email': address.email,
            }
            address_list.append(address_dict)

        context = {
            'addresses': address_list,
            'default_address_id': user.default_address_id
        }
        return render(request, 'user_center_site.html', context)


class CreateAddressView(LoginRequiredView):
    """新增收货地址"""

    def post(self, request):
        """新增收货地址逻辑"""
        user = request.user
        # 判断用户的收货地址数据,如果超过20个提前响应
        count = Address.objects.filter(user=user, is_deleted=False).count()
        # count = user.addresses.count()
        if count >= 20:
            return http.HttpResponseForbidden('用户收货地址上限')
        # 接收请求数据
        json_dict = json.loads(request.body.decode())
        """
            title: '',
            receiver: '',
            province_id: '',
            city_id: '',
            district_id: '',
            place: '',
            mobile: '',
            tel: '',
            email: '',
        """
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验
        if all([title, receiver, province_id, city_id, district_id, place, mobile]) is False:
            return http.HttpResponseForbidden('缺少必传参数')

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        # 新增
        try:
            address = Address.objects.create(
                user=user,
                title=title,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
            if user.default_address is None:  # 判断当前用户是否有默认收货地址
                user.default_address = address  # 就把当前的收货地址设置为它的默认值
                user.save()
        except Exception:
            return http.HttpResponseForbidden('新增地址出错')

        # 把新增的地址数据响应回去
        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province_id': address.province_id,
            'province': address.province.name,
            'city_id': address.city_id,
            'city': address.city.name,
            'district_id': address.district_id,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email,
        }
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'address': address_dict})


class UpdateDestroyAddressView(LoginRequiredView):
    """修改和删除"""

    def put(self, request, address_id):
        """修改地址逻辑"""
        # 查询要修改的地址对象
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('要修改的地址不存在')


        # 接收
        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        # 校验
        if all([title, receiver, province_id, city_id, district_id, place, mobile]) is False:
            return http.HttpResponseForbidden('缺少必传参数')

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')


        # 修改
        Address.objects.filter(id=address_id).update(
            title=title,
            receiver=receiver,
            province_id=province_id,
            city_id=city_id,
            district_id=district_id,
            place=place,
            mobile=mobile,
            tel=tel,
            email=email
        )
        address = Address.objects.get(id=address_id)  # 要重新查询一次新数据
        # 把新增的地址数据响应回去
        address_dict = {
            'id': address.id,
            'title': address.title,
            'receiver': address.receiver,
            'province_id': address.province_id,
            'province': address.province.name,
            'city_id': address.city_id,
            'city': address.city.name,
            'district_id': address.district_id,
            'district': address.district.name,
            'place': address.place,
            'mobile': address.mobile,
            'tel': address.tel,
            'email': address.email,
        }
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'address': address_dict})
        # 响应

    def delete(self, request, address_id):
        """对收货地址逻辑删除"""
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('要删除的地址不存在')

        address.is_deleted = True
        # address.delete()
        address.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class DefaultAddressView(LoginRequiredView):
    """设置默认地址"""

    def put(self, request, address_id):
        """实现默认地址"""
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('要修改的地址不存在')

        user = request.user
        user.default_address = address
        user.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class UpdateTitleAddressView(LoginRequiredView):
    """修改用户收货地址标题"""
    def put(self, request, address_id):
        try:
            address = Address.objects.get(id=address_id)
        except Address.DoesNotExist:
            return http.HttpResponseForbidden('要修改的地址不存在')

        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')
        address.title = title
        address.save()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class ChangePasswordView(LoginRequiredView):
    """修改密码"""

    def get(self, request):
        return render(request, 'user_center_pass.html')


    def post(self, request):
        """实现修改密码逻辑"""

        # 接收参数
        old_password = request.POST.get('old_pwd')
        password = request.POST.get('new_pwd')
        password2 = request.POST.get('new_cpwd')

        # 校验
        if all([old_password, password, password2]) is False:
            return http.HttpResponseForbidden("缺少必传参数")

        user = request.user
        if user.check_password(old_password) is False:
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '原始密码错误'})

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('密码最少8位，最长20位')
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')

        # 修改密码
        user.set_password(password)
        user.save()

        # 响应重定向到登录界面
        logout(request)
        response = redirect('/login/')
        response.delete_cookie('username')

        return response


# class UserBrowseHistory(View):
#     """用户商品浏览记录"""
#
#     def post(self, request):
#
#         # 判断当前用户是否登录
#         user = request.user
#         if not user.is_authenticated:
#             return http.JsonResponse({'code': RETCODE.SESSIONERR, 'errmsg': '用户未登录'})
#
#         # 获取请求体中的sku_id
#         json_dict = json.loads(request.body.decode())
#         sku_id = json_dict.get('sku_id')
#
#         # 校验sku_id
#         try:
#             sku = SKU.objects.get(id=sku_id)
#         except SKU.DoesNotExist:
#             return http.HttpResponseForbidden('sku_id不存在')
#
#         # 创建redis连接对象
#         redis_conn = get_redis_connection('history')
#         pl = redis_conn.pipeline()
#
#         key = 'history_%s' % user.id
#         # 先去重
#         pl.lrem(key, 0, sku_id)
#
#         # 存储到列表的开头
#         pl.lpush(key, sku_id)
#
#         # 截取前5个
#         pl.ltrim(key, 0, 4)
#         # 执行管道
#         pl.execute()
#
#         # 响应
#         return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})
#
#     def get(self, request):
#         """浏览记录查询"""
#
#         # 创建redis连接对象
#         redis_conn = get_redis_connection('history')
#         sku_id_list = redis_conn.lrange('history_%s' % request.user.id, 0, -1)
#         # 获取当前登录用户的浏览记录列表数据 [sku_id1, sku_id2]
#
#         # 通过sku_id查询sku,再将sku模型转换成字典
#         # sku_qs = SKU.objects.filter(id__in=sku_id_list)  [b'3', b'2', b'5'] [2, 3, 5]
#         skus = []  # 用来装每一个sku字典
#         for sku_id in sku_id_list:
#             sku = SKU.objects.get(id=sku_id)
#             sku_dict = {
#                 'id': sku.id,
#                 'name': sku.name,
#                 'default_image_url': sku.default_image.url,
#                 'price': sku.price
#             }
#             skus.append(sku_dict)
#         # 响应
#         return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': skus})
#
