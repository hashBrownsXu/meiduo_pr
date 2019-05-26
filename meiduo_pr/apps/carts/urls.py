from django.contrib.auth.decorators import login_required
from django.conf.urls import url, include
from django.contrib import admin
from . import views
urlpatterns = [

    # 购物车url
    url(r'^carts/$', views.CartsView.as_view(), name='carts'),

]
