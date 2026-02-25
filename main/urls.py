from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='login/', permanent=False)),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('login_page/', views.login_page, name='login_page'),  # ✅ Add this line
    path('generate/', views.generate_outfit, name='generate_outfit'),
    path('register/', views.register, name='register'),  
    path('segment_shirt/', views.segment_shirt, name='segment_shirt'),
]
