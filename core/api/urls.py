from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView, TokenVerifyView,
)
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView,
)
from .views import (
    DoctorViewSet, PatientViewSet, AppointmentViewSet,
    VitalSignsViewSet, MedicalRecordViewSet, PrescriptionViewSet,
    BillViewSet, NotificationViewSet,
    AnalyticsSummaryView, AnalyticsChartsView,
)

router = DefaultRouter()
router.register(r'doctors',       DoctorViewSet,        basename='api-doctor')
router.register(r'patients',      PatientViewSet,       basename='api-patient')
router.register(r'appointments',  AppointmentViewSet,   basename='api-appointment')
router.register(r'vitals',        VitalSignsViewSet,    basename='api-vitals')
router.register(r'records',       MedicalRecordViewSet, basename='api-record')
router.register(r'prescriptions', PrescriptionViewSet,  basename='api-prescription')
router.register(r'bills',         BillViewSet,          basename='api-bill')
router.register(r'notifications', NotificationViewSet,  basename='api-notification')

urlpatterns = [
    # ViewSets
    path('', include(router.urls)),

    # Analytics
    path('analytics/summary/', AnalyticsSummaryView.as_view(), name='api-analytics-summary'),
    path('analytics/charts/',  AnalyticsChartsView.as_view(),  name='api-analytics-charts'),

    # JWT auth
    path('token/',          TokenObtainPairView.as_view(),  name='token_obtain_pair'),
    path('token/refresh/',  TokenRefreshView.as_view(),     name='token_refresh'),
    path('token/verify/',   TokenVerifyView.as_view(),      name='token_verify'),

    # Browsable API login
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),

    # OpenAPI schema + Swagger UI + ReDoc
    path('schema/',      SpectacularAPIView.as_view(),                              name='api-schema'),
    path('docs/',        SpectacularSwaggerView.as_view(url_name='api-schema'),     name='api-docs'),
    path('docs/redoc/',  SpectacularRedocView.as_view(url_name='api-schema'),       name='api-redoc'),
]
