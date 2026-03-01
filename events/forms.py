from django import forms
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
