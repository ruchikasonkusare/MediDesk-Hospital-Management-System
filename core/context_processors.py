from .models import UserProfile

def user_role(request):
    """Safely inject user role into every template context."""
    if not request.user.is_authenticated:
        return {'user_role': '', 'user_profile': None}
    if request.user.is_superuser:
        return {'user_role': 'admin', 'user_profile': None}
    try:
        profile = request.user.profile
        return {'user_role': profile.role, 'user_profile': profile}
    except Exception:
        # Auto-create missing profile
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'role': 'receptionist'}
        )
        return {'user_role': profile.role, 'user_profile': profile}
