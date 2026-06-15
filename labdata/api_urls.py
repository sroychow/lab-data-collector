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
    path(
        "experiments/<slug:slug>/submissions/",
        api.ExperimentSubmissionCreateAPIView.as_view(),
        name="api_experiment_submission_create",
    ),

    path("submissions/", api.SubmissionListAPIView.as_view(), name="api_submission_list"),
    path("submissions/<int:pk>/", api.SubmissionDetailAPIView.as_view(), name="api_submission_detail"),
    path(
        "submissions/<int:pk>/plots/<int:plot_id>/",
        api.SubmissionPlotAPIView.as_view(),
        name="api_submission_plot",
    ),
]
