from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.
class UserProfile(models.Model):
    sso_user_id=models.PositiveBigIntegerField(unique=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    terms_accepted_at = models.DateTimeField(auto_now_add=True)

    user = models.OneToOneField(
        get_user_model(),
        related_name='profile',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f'SSO_ID={self.sso_user_id} - LOCAL_ID={self.user.id} - LOCAL_USERNAME={self.user.username}'