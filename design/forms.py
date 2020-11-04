"""Primer3 input form.

For details on input params see:
https://primer3.org/manual.html#globalTags
"""

from django import forms
from .fasta import Fasta


class PrimerForm(forms.Form):
    """Collect user input to run primer prediction."""

    fasta = forms.CharField(initial="")
    # Primer size range
    primer_min = forms.IntegerField(initial=18)
    primer_max = forms.IntegerField(initial=27)
    primer_optimum = forms.IntegerField(initial=20)
    # Amplicon size range
    amplicon_min = forms.IntegerField(initial=50)
    amplicon_max = forms.IntegerField(initial=600)
    # Primer melting temperature range
    tm_min = forms.FloatField(initial=59)
    tm_max = forms.FloatField(initial=61)
    tm_optimum = forms.FloatField(initial=60)
    # Max self complement
    self_dimer_any = forms.FloatField(initial=8.0)
    # Max self complement 3'
    self_dimer_end = forms.FloatField(initial=3.0)
    # GC content
    gc_min = forms.FloatField(initial=20.0)
    gc_clamp = forms.IntegerField(initial=0)

    def clean(self):
        """Validate and return user input."""
        data = self.cleaned_data
        data['fasta'] = Fasta.from_string(data['fasta'])
        return data
