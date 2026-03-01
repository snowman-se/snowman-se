from django.db import models
from django.contrib.auth.models import User


class Event(models.Model):
    title = models.CharField(max_length=100)
    host = models.CharField(max_length=50)
    venue = models.CharField(max_length=100)
    start_at = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    body = models.TextField()
    poster = models.ImageField(upload_to='posters/', blank=True, null=True)
    is_public = models.BooleanField(default=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_events')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def attendee_count(self):
        return Attendance.objects.filter(event=self, is_waiting=False).count()

    def is_full(self):
        return self.attendee_count() >= self.capacity

    @property
    def tags(self):
        return Tag.objects.filter(eventtag__event=self)


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#007bff')

    def __str__(self):
        return self.name


class EventTag(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('event', 'tag')

    def __str__(self):
        return f'{self.event} - {self.tag}'


class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
    is_waiting = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')

    def __str__(self):
        return f'{self.user} - {self.event}'
