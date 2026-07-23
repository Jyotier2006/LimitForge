from django.http import JsonResponse
from django.urls import path


def home(request):
    return JsonResponse({"message": "Refresh until HTTP 429 appears."})


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("", home),
    path("strict/", home),
    path("health/", health),
]
