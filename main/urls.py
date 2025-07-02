from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_page, name='login'),
    path("generate/", views.generate_outfit, name="generate_outfit"),
]
