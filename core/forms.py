from django import forms


class BootstrapFormMixin:
    """Adds Bootstrap 5 classes to every widget and marks invalid fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.RadioSelect):
                continue
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        super().full_clean()
        if self._errors:
            for name in self._errors:
                if name in self.fields:
                    widget = self.fields[name].widget
                    widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()
