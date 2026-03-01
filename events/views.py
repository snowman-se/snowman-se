import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView,
)

from .forms import EventForm
from .models import Attendance, Event, EventTag, Tag

logger = logging.getLogger(__name__)


class EventListView(ListView):
    model = Event
    template_name = 'events/event_list.html'
    paginate_by = 10

    def get_queryset(self):
        qs = Event.objects.filter(is_public=True)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(host__icontains=q) |
                Q(venue__icontains=q) |
                Q(eventtag__tag__name__icontains=q)
            ).distinct()
        order = self.request.GET.get('order', 'start_at_asc')
        if order == 'start_at_desc':
            qs = qs.order_by('-start_at')
        elif order == 'created_desc':
            qs = qs.order_by('-created_at')
        else:
            qs = qs.order_by('start_at')
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['order'] = self.request.GET.get('order', 'start_at_asc')
        return ctx


class EventDetailView(DetailView):
    model = Event
    template_name = 'events/event_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        event = self.object
        ctx['tags'] = event.tags
        ctx['attendees'] = Attendance.objects.filter(event=event, is_waiting=False).select_related('user')
        ctx['waitlist'] = Attendance.objects.filter(event=event, is_waiting=True).select_related('user')
        ctx['attendee_count'] = event.attendee_count()
        user_attendance = None
        if self.request.user.is_authenticated:
            user_attendance = Attendance.objects.filter(user=self.request.user, event=event).first()
        ctx['user_attendance'] = user_attendance
        ctx['can_edit'] = (
            self.request.user.is_authenticated and
            (self.request.user == event.owner or self.request.user.is_staff)
        )
        return ctx


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['all_tags'] = Tag.objects.all()
        return ctx

    def form_valid(self, form):
        form.instance.owner = self.request.user
        self.object = form.save()
        tag_pks = self.request.POST.getlist('tags')
        EventTag.objects.filter(event=self.object).delete()
        for pk in tag_pks:
            try:
                tag = Tag.objects.get(pk=pk)
                EventTag.objects.get_or_create(event=self.object, tag=tag)
            except Tag.DoesNotExist:
                pass
        logger.info('Event created: %s by %s', self.object.title, self.request.user)
        messages.success(self.request, 'イベントを作成しました。')
        return redirect('event_detail', pk=self.object.pk)


class EventUpdateView(LoginRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = 'events/event_form.html'

    def dispatch(self, request, *args, **kwargs):
        obj = get_object_or_404(Event, pk=kwargs['pk'])
        if not request.user.is_staff and obj.owner != request.user:
            messages.error(request, '編集権限がありません。')
            return redirect('event_detail', pk=obj.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['all_tags'] = Tag.objects.all()
        return ctx

    def form_valid(self, form):
        self.object = form.save()
        tag_pks = self.request.POST.getlist('tags')
        EventTag.objects.filter(event=self.object).delete()
        for pk in tag_pks:
            try:
                tag = Tag.objects.get(pk=pk)
                EventTag.objects.get_or_create(event=self.object, tag=tag)
            except Tag.DoesNotExist:
                pass
        logger.info('Event updated: %s by %s', self.object.title, self.request.user)
        messages.success(self.request, 'イベントを更新しました。')
        return redirect('event_detail', pk=self.object.pk)


class EventDeleteView(LoginRequiredMixin, DeleteView):
    model = Event
    template_name = 'events/event_confirm_delete.html'
    success_url = '/events/'

    def dispatch(self, request, *args, **kwargs):
        obj = get_object_or_404(Event, pk=kwargs['pk'])
        if not request.user.is_staff and obj.owner != request.user:
            messages.error(request, '削除権限がありません。')
            return redirect('event_detail', pk=obj.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        event_title = self.object.title
        response = super().form_valid(form)
        logger.info('Event deleted: %s by %s', event_title, self.request.user)
        messages.success(self.request, 'イベントを削除しました。')
        return response


class JoinView(LoginRequiredMixin, View):
    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        if Attendance.objects.filter(user=request.user, event=event).exists():
            messages.error(request, 'すでに登録済みです。')
            return redirect('event_detail', pk=pk)
        if event.attendee_count() < event.capacity:
            Attendance.objects.create(user=request.user, event=event, is_waiting=False)
            messages.success(request, 'イベントに参加登録しました。')
        else:
            Attendance.objects.create(user=request.user, event=event, is_waiting=True)
            messages.success(request, '満員のためキャンセル待ちに登録しました。')
        return redirect('event_detail', pk=pk)


class CancelView(LoginRequiredMixin, View):
    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        attendance = get_object_or_404(Attendance, user=request.user, event=event)
        was_attending = not attendance.is_waiting
        attendance.delete()
        if was_attending:
            first_waiting = Attendance.objects.filter(event=event, is_waiting=True).order_by('created_at').first()
            if first_waiting:
                first_waiting.is_waiting = False
                first_waiting.save()
        messages.success(request, '参加をキャンセルしました。')
        return redirect('event_detail', pk=pk)


class MyPageView(LoginRequiredMixin, TemplateView):
    template_name = 'events/my_page.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hosted_events'] = Event.objects.filter(owner=self.request.user)
        ctx['attending'] = Attendance.objects.filter(
            user=self.request.user, is_waiting=False
        ).select_related('event')
        ctx['waiting'] = Attendance.objects.filter(
            user=self.request.user, is_waiting=True
        ).select_related('event')
        return ctx


def health_check(request):
    return JsonResponse({"ok": True})
