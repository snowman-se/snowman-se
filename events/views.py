import base64
import io
import logging

import pyotp
import qrcode
from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView,
)

from .forms import EventForm, SignUpForm
from .models import Attendance, Event, EventTag, Tag, TOTPDevice

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Authentication                                                                #
# --------------------------------------------------------------------------- #

class CustomLoginView(LoginView):
    """Standard login, but redirects to TOTP verify step when 2FA is active."""

    def form_valid(self, form):
        user = form.get_user()
        device = TOTPDevice.objects.filter(user=user, is_verified=True).first()
        if device:
            # Store partial-auth state in session; don't call auth_login yet.
            self.request.session['pre_2fa_user_id'] = user.pk
            self.request.session['pre_2fa_backend'] = user.backend
            next_url = self.request.POST.get('next') or self.get_success_url()
            self.request.session['pre_2fa_next'] = next_url
            return redirect('two_factor_verify')
        # No 2FA — normal login
        return super().form_valid(form)


class TwoFactorVerifyView(View):
    """Enter TOTP code to complete a login that was interrupted for 2FA."""

    template_name = 'registration/two_factor_verify.html'

    def dispatch(self, request, *args, **kwargs):
        if 'pre_2fa_user_id' not in request.session:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        from django.contrib.auth.models import User
        user_id = request.session.get('pre_2fa_user_id')
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return redirect('login')

        code = request.POST.get('code', '').strip()
        try:
            device = user.totp_device
        except TOTPDevice.DoesNotExist:
            messages.error(request, '二段階認証の設定が見つかりません。再度ログインしてください。')
            return redirect('login')
        totp = pyotp.TOTP(device.secret)
        if totp.verify(code):
            backend = request.session.pop('pre_2fa_backend',
                                          'django.contrib.auth.backends.ModelBackend')
            next_url = request.session.pop('pre_2fa_next',
                                           django_settings.LOGIN_REDIRECT_URL)
            del request.session['pre_2fa_user_id']
            auth_login(request, user, backend=backend)
            return redirect(next_url)

        messages.error(request, 'コードが正しくありません。もう一度お試しください。')
        return render(request, self.template_name)


class TwoFactorSetupView(LoginRequiredMixin, View):
    """Generate a TOTP secret and confirm it by asking the user to verify once."""

    template_name = 'registration/two_factor_setup.html'

    def _render(self, request, device):
        totp = pyotp.TOTP(device.secret)
        uri = totp.provisioning_uri(
            name=request.user.username,
            issuer_name='EventBoard+',
        )
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
        return render(request, self.template_name, {
            'secret': device.secret,
            'qr_code': qr_b64,
        })

    def get(self, request):
        device, _ = TOTPDevice.objects.get_or_create(
            user=request.user,
            defaults={'secret': pyotp.random_base32()},
        )
        if device.is_verified:
            messages.info(request, '二段階認証はすでに有効です。')
            return redirect('my_page')
        return self._render(request, device)

    def post(self, request):
        device = get_object_or_404(TOTPDevice, user=request.user)
        code = request.POST.get('code', '').strip()
        totp = pyotp.TOTP(device.secret)
        if totp.verify(code):
            device.is_verified = True
            device.save()
            logger.info('2FA enabled for user: %s', request.user)
            messages.success(request, '二段階認証を有効にしました。')
            return redirect('my_page')
        messages.error(request, 'コードが正しくありません。もう一度お試しください。')
        return self._render(request, device)


class TwoFactorDisableView(LoginRequiredMixin, View):
    """Disable 2FA for the current user."""

    def post(self, request):
        TOTPDevice.objects.filter(user=request.user).delete()
        logger.info('2FA disabled for user: %s', request.user)
        messages.success(request, '二段階認証を無効にしました。')
        return redirect('my_page')


class SignUpView(View):
    """User registration: full name, email or phone, password."""

    template_name = 'registration/signup.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('event_list')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {'form': SignUpForm()})

    def post(self, request):
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user,
                       backend='django.contrib.auth.backends.ModelBackend')
            logger.info('New user registered: %s', user.username)
            messages.success(request, 'アカウントを作成しました。ようこそ！')
            return redirect('event_list')
        return render(request, self.template_name, {'form': form})


# --------------------------------------------------------------------------- #
# Events                                                                        #
# --------------------------------------------------------------------------- #

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
        device = TOTPDevice.objects.filter(user=self.request.user, is_verified=True).first()
        ctx['two_factor_enabled'] = device is not None
        return ctx


def health_check(request):
    return JsonResponse({"ok": True})
