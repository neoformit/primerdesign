"""Primer3 input form.

For details on input params see:
https://primer3.org/manual.html#globalTags
"""

from django import forms
from django.core.exceptions import ValidationError

from .fasta import Fasta


class PrimerForm(forms.Form):
    """Collect user input to run primer prediction."""

    fasta = forms.CharField(initial="")
    # Primer size range
    primer_min = forms.IntegerField(initial=18, max_value=35)
    primer_max = forms.IntegerField(initial=27, max_value=35)
    primer_optimum = forms.IntegerField(initial=20, max_value=35)
    # Amplicon size range
    amplicon_min = forms.IntegerField(
        initial=60, min_value=50, max_value=20000)
    amplicon_max = forms.IntegerField(
        initial=80, min_value=50, max_value=20000)
    # Primer melting temperature range
    tm_min = forms.FloatField(initial=59, min_value=0, max_value=100)
    tm_max = forms.FloatField(initial=61, min_value=0, max_value=100)
    tm_optimum = forms.FloatField(initial=60, min_value=0, max_value=100)
    # Max self complement
    self_dimer_any = forms.FloatField(
        initial=8.0, min_value=0, max_value=9999.99)
    # Max self complement 3'
    self_dimer_end = forms.FloatField(
        initial=3.0, min_value=0, max_value=9999.99)
    # GC content
    gc_min = forms.FloatField(initial=20.0, min_value=0, max_value=100)
    gc_clamp = forms.IntegerField(initial=0)

    def clean(self):
        """Validate and return user input."""
        data = self.cleaned_data
        data['fasta'] = Fasta.from_string(data['fasta'])
        validate_fasta(data)
        return data


def validate_fasta(data):
    """Validate input sequence lengths."""
    for sequence in data['fasta'].values():
        print(f'Sequence length {len(sequence)} nt')
        if len(sequence) < data['amplicon_min']:
            raise ValidationError({'fasta':
                f'Input sequence must be longer than minimum'
                + f' amplicon length parameter ({data["amplicon_min"]} nt)'
            })
