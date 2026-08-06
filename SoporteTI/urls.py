from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
import os

def serviceworker(request):
    sw_path = os.path.join(settings.BASE_DIR, 'SoporteTI', 'static', 'serviceworker.js')
    with open(sw_path, 'r') as f:
        content = f.read()
    response = HttpResponse(content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response

urlpatterns = [
    path('admin/', admin.site.urls),

    # Service Worker en la raíz (necesario para scope /)
    path('serviceworker.js', serviceworker, name='serviceworker'),

    # Login nativo de Django con plantilla personalizada
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html',
        redirect_authenticated_user=True,
    ), name='login'),

    # Todas las rutas de la app Helpdesk
    path('', include('Helpdesk.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
