from django.db import models

# Create your models here.

class ContactMessage(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"
    

    REPORT_REASON_CHOICES = [
        ('spam', 'Spam ou contenu trompeur'),
        ('harcèlement', 'Harcèlement ou intimidation'),
        ('haine', 'Discours de haine ou symboles'),
        ('violence', 'Violence ou actes dangereux'),
        ('autre', 'Autre'),
    ]

    name = models.CharField(max_length=255)
    email = models.EmailField()
    reason = models.CharField(max_length=50, choices=REPORT_REASON_CHOICES)
    reported_url = models.URLField()
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} a signalé {self.reported_url}"