from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_health(request):
    return JsonResponse({
        'service': 'The Masters Barber & Executive Spa API',
        'status': 'healthy',
        'version': '1.0.0'
    })

urlpatterns = [
    path('', api_health, name='api-health'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]
