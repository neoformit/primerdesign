from django import forms
from .fasta import Fasta


class PrimerForm(forms.Form):
    """Collect user input to run primer prediction."""

    fasta = forms.CharField(initial="")
    # Primer size range
    primer_min = forms.IntegerField(initial=18)
    primer_max = forms.IntegerField(initial=27)
    primer_optimum = forms.IntegerField(initial=20)
    # Primer melting temperature range
    tm_min = forms.FloatField(initial=59)
    tm_max = forms.FloatField(initial=61)
    tm_optimum = forms.FloatField(initial=60)
    # Max self complement
    self_dimer_any = forms.FloatField(initial=8.0)
    # Max self complement 3'
    self_dimer_end = forms.FloatField(initial=3.0)
    # GC clamp
    gc_clamp = forms.IntegerField(initial=0)

    def clean(self):
        """Validate and return user input."""
        data = self.cleaned_data
        data['fasta'] = Fasta.from_string(data['fasta'])
        return data
