from django.urls import path
from . import views

app_name = 'contacts'

urlpatterns = [
    path('messages/', views.contact_message_create, name='contact_message_create'),
]