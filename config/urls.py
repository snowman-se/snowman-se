from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from events.views import (
    health_check,
    CustomLoginView,
    TwoFactorVerifyView,
    TwoFactorSetupView,
    TwoFactorDisableView,
    SignUpView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # Custom login (must come before the auth include to override the default)
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    # User registration
    path('accounts/register/', SignUpView.as_view(), name='signup'),
    # Two-factor authentication
    path('accounts/two-factor/setup/', TwoFactorSetupView.as_view(), name='two_factor_setup'),
    path('accounts/two-factor/verify/', TwoFactorVerifyView.as_view(), name='two_factor_verify'),
    path('accounts/two-factor/disable/', TwoFactorDisableView.as_view(), name='two_factor_disable'),
    # Standard auth views (password reset, logout, etc.)
    path('accounts/', include('django.contrib.auth.urls')),
    path('health/', health_check, name='health_check'),
    path('', RedirectView.as_view(url='/events/', permanent=False)),
    path('', include('events.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
