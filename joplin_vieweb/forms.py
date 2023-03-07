from django import forms


SYNCH_TARGET_CHOICES = (
    (0, "Synchronisation disabled"),
    (5, "Nextcloud"),
    (6, "WebDAV"),
    (9, "Joplin server"),
    (1000, "You need another one? Ask on github issues."),
)

SYNCH_INTERVAL_CHOICES = (
    (0, "Manual synchronisation"),
    (300, "5 minutes"),
    (600, "10 minutes"),
    (1800, "30 minutes"),
    (3600, "1 hour"),
    (43200, "12 hours"),
    (86400, "1 day"),
) 


class ConfigForm(forms.Form):
    target = forms.ChoiceField(label="Synchronisation target", choices=SYNCH_TARGET_CHOICES)
    path = forms.URLField(label="Synchronisation url", widget=forms.TextInput(attrs={'size': 80}))
    username = forms.CharField(label="Username", widget=forms.TextInput(attrs={'size': 80}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(render_value=True, attrs={"autocomplete": "off", "size": 80}))
    interval = forms.ChoiceField(label="Interval", choices=SYNCH_INTERVAL_CHOICES)
    