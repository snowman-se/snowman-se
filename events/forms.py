import re

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email as _validate_email
from django.db.models import Q

from .models import Event, Tag


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'host', 'venue', 'start_at', 'capacity', 'body', 'poster', 'is_public']
        widgets = {
            'start_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['poster'].help_text = 'JPG/PNG, 最大2MB'
        self.fields['start_at'].input_formats = ['%Y-%m-%dT%H:%M']
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                widget = field.widget
                if widget.__class__.__name__ in ('CheckboxInput',):
                    widget.attrs.setdefault('class', 'form-check-input')
                else:
                    widget.attrs.setdefault('class', 'form-control')

    def clean_poster(self):
        poster = self.cleaned_data.get('poster')
        if poster and hasattr(poster, 'content_type'):
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
            if poster.content_type not in allowed_types:
                raise forms.ValidationError('JPGまたはPNG形式のファイルのみアップロード可能です。')
            if poster.size > 2 * 1024 * 1024:
                raise forms.ValidationError('ファイルサイズは2MB以内にしてください。')
        return poster


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'color']


class SignUpForm(forms.Form):
    """Registration form: full name, email or phone, password + confirmation."""

    full_name = forms.CharField(
        max_length=150,
        label='氏名',
        widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
    )
    email_or_phone = forms.CharField(
        max_length=150,
        label='メールアドレスまたは携帯電話番号',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    password1 = forms.CharField(
        label='パスワード',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='パスワード（確認）',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    PHONE_RE = re.compile(r'^\+?[\d\s\-\(\)]{10,20}$')

    def _looks_like_email(self, value):
        return '@' in value

    def clean_full_name(self):
        return self.cleaned_data['full_name'].strip()

    def clean_email_or_phone(self):
        value = self.cleaned_data['email_or_phone'].strip()
        if self._looks_like_email(value):
            try:
                _validate_email(value)
            except forms.ValidationError:
                raise forms.ValidationError('有効なメールアドレスを入力してください。')
            if User.objects.filter(
                Q(username=value[:150]) | Q(email=value)
            ).exists():
                raise forms.ValidationError('このメールアドレスはすでに登録されています。')
        elif self.PHONE_RE.match(value):
            normalized = re.sub(r'[\s\-\(\)]', '', value)
            if User.objects.filter(username=normalized).exists():
                raise forms.ValidationError('この電話番号はすでに登録されています。')
        else:
            raise forms.ValidationError(
                '有効なメールアドレスまたは携帯電話番号を入力してください。'
                '（例: example@email.com または 08012345678）'
            )
        return value

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            user = User(
                username=self.cleaned_data.get('email_or_phone', ''),
                first_name=self.cleaned_data.get('full_name', ''),
            )
            validate_password(password, user=user)
        return password

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1', '')
        p2 = self.cleaned_data.get('password2', '')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('パスワードが一致しません。')
        return p2

    def save(self):
        full_name = self.cleaned_data['full_name']
        value = self.cleaned_data['email_or_phone'].strip()
        password = self.cleaned_data['password1']

        if self._looks_like_email(value):
            username = value[:150]
            email = value
        else:
            username = re.sub(r'[\s\-\(\)]', '', value)
            email = ''

        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name,
        )
