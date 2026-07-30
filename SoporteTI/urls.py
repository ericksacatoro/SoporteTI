from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Login nativo de Django con plantilla personalizada
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True,
    ), name='login'),

    # Todas las rutas de la app Helpdesk (sin namespace para compatibilidad con redirects directos)
    path('', include('Helpdesk.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
