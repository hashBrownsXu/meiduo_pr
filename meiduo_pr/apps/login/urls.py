
from django.conf.urls import url, include
from django.contrib import admin
from . import views
urlpatterns = [
    url(r'^login', views.LoginView.as_view(), name='login')

]
