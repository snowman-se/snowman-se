from django.urls import path
from . import views

urlpatterns = [
    path('events/', views.EventListView.as_view(), name='event_list'),
    path('events/create/', views.EventCreateView.as_view(), name='event_create'),
    path('events/my/', views.MyPageView.as_view(), name='my_page'),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('events/<int:pk>/edit/', views.EventUpdateView.as_view(), name='event_edit'),
    path('events/<int:pk>/delete/', views.EventDeleteView.as_view(), name='event_delete'),
    path('events/<int:pk>/join/', views.JoinView.as_view(), name='event_join'),
    path('events/<int:pk>/cancel/', views.CancelView.as_view(), name='event_cancel'),
]
