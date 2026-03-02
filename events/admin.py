from django.contrib import admin
from .models import Event, Tag, EventTag, Attendance


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'host', 'venue', 'start_at', 'capacity', 'is_public', 'owner', 'created_at')
    list_filter = ('is_public', 'start_at')
    search_fields = ('title', 'host', 'venue')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')


@admin.register(EventTag)
class EventTagAdmin(admin.ModelAdmin):
    list_display = ('event', 'tag')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'is_waiting', 'created_at')
    list_filter = ('is_waiting',)
