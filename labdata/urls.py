from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("experiments/", views.experiment_list, name="experiment_list"),
    path("experiments/new/", views.experiment_create, name="experiment_create"),
    path("experiments/<slug:slug>/", views.experiment_detail, name="experiment_detail"),
    path("experiments/<slug:slug>/submit/", views.submit_data, name="submit_data"),
    path("experiments/<slug:slug>/export.csv", views.export_csv, name="export_csv"),
    path("submissions/<int:pk>/", views.submission_detail, name="submission_detail"),
    path(
        "submissions/<int:pk>/plots/<int:plot_id>/",
        views.submission_plot_detail,
        name="submission_plot_detail",
    ),
    path("plots/<int:plot_id>/", views.plot_detail, name="plot_detail"),
]
