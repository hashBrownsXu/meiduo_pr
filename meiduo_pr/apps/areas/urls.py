from django.contrib.auth.decorators import login_required
from django.conf.urls import url, include
from django.contrib import admin
from . import views
urlpatterns = [

    # 用户收货地址查询
    url(r'^areas/$', views.AreasView.as_view(), name='areas'),

]
