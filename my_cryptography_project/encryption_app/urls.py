from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('encrypt/', views.encrypt_file, name='encrypt'),
    path('decrypt/', views.decrypt_file, name='decrypt'),
]
