from django.urls import path
from . import views

urlpatterns = [
    path('login_user', views.login_user, name="login"),
    path('logout_user', views.logout_user, name='logout'),
    path('register_user', views.register_user, name='register_user'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('user_bookings/<int:user_id>/', views.user_bookings, name='user_bookings'),
    path('view_bookings/<int:booking_id>/', views.view_bookings, name='view_bookings'),
    path('cancel_booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
]