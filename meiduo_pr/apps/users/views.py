from django.shortcuts import render, redirect
from django.views import View
from django import http
import re
from .models import User
from django.db import DatabaseError
from django.contrib.auth import login
import logging
from meiduo_pr.utils.response_code import RETCODE

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
            logging.error(e)
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

    # Create your views here.