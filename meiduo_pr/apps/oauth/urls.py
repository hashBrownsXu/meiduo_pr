from django.conf.urls import url

from . import views

urlpatterns = [
    # 获取QQ登录界面url
    url(r'^qq/authorization/$', views.OAuthURLView.as_view()),
    # QQ登录成功后的回调处理
    url(r'^oauth_callback/$', views.OAuthUserView.as_view()),
]