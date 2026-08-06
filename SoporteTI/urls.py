from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # PWA (manifest.json + serviceworker.js) — debe ir antes de las rutas de la app
    path('', include('pwa.urls')),

    # Login nativo de Django con plantilla personalizada
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True,
    ), name='login'),

    # Todas las rutas de la app Helpdesk
    path('', include('Helpdesk.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
