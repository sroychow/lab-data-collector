from django.urls import path

from . import api


urlpatterns = [
    path("health/", api.health_check, name="api_health"),
    path("login/", api.api_login, name="api_login"),
    path("experiments/", api.ExperimentListAPIView.as_view(), name="api_experiment_list"),
    path(
        "experiments/<slug:slug>/schema/",
        api.ExperimentSchemaAPIView.as_view(),
        name="api_experiment_schema",
    ),
]
