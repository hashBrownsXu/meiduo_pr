from django.shortcuts import render
from django.views import View


class RegisterView(View):

    def get(self, request):
        return render(request, 'register.html')


# Create your views here.
