from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden, HttpResponse
from django.views import View


class IndexView(View):
    def get(self, request):
        return render(request, 'index.html')
# Create your views here.
