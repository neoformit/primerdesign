"""A wrapper around the primer3 software."""

import os
import string
import random
import subprocess
# from django.conf import settings
# from django.template.loader import render_to_string


class PrimerDesign:
    """Analyse a target DNA sequence with primer3 for potential primers."""

    def __init__(self, params):
        """Run primer3 with the given target sequences and render output."""
        self.params = params
        self.iterations = self.run(params)

    def __str__(self):
        """Render output to string."""
        return

    def __iter__(self):
        """Iterate through result sequences."""
        self.index = 0
        return self

    def __next__(self):
        """Return next sequence in iteration."""
        if self.index <= len(self.iterations):
            this = self.iterations[self.index]
            self.index += 1
            return this
        raise StopIteration

    def create_input(self, params):
        """Parse the target parameters to a primer3 input file."""
        alphanumeric = string.ascii_letters + string.digits
        input_path = os.path.join(
            settings.PRIMER3_INPUT_DIR,
            '%s.conf' % ''.join([
                random.choice(alphanumeric)
                for i in range(12)
            ])
        )
        with open(input_path, 'w') as f:
            f.write(render_to_string('design/input.template', params))
        return input_path

    def run(self, params):
        """Analyse the target sequence with primer3."""
        input_path = self.create_input(params)
        args = [
            settings.PRIMER3_PATH,
            input_path,
        ]
        result = subprocess.run(args, check=True, capture_output=True)
        os.remove(input_path)
        return [
            Iteration(x)
            for x in result.stdout.split('\n=\n')
            if x.startswith('SEQUENCE_ID')
        ]


class Iteration:
    """Holds primer predictions for a single query sequence."""

    def __init__(self, output):
        """Parse iteration data from output string."""
        data = {
            line.split('=')[0]: line.split('=')[1]
            for line in output.split('\n')
        }
        self.name = data['SEQUENCE_ID']
        self.sequence = data['SEQUENCE_TEMPLATE']
        self.explanation = {
            'pair': data['PRIMER_PAIR_EXPLAIN'],
            'left': data['PRIMER_LEFT_EXPLAIN'],
            'right': data['PRIMER_RIGHT_EXPLAIN'],
        }
        self.primer_count = {
            'pair': data['PRIMER_PAIR_NUM_RETURNED'],
            'left': data['PRIMER_LEFT_NUM_RETURNED'],
            'right': data['PRIMER_RIGHT_NUM_RETURNED'],
            'internal': data['PRIMER_INTERNAL_NUM_RETURNED'],
        }
        self.primers = self.parse_primers(data, self.sequence)

    def parse_primers(self, data, sequence_template):
        """Parse primer pairs from output dict."""
        def key_matches_index(i, key):
            """Parse int index from key string."""
            try:
                return key.split('_')[2] == str(i)
            except IndexError:
                return False

        i = 0
        primers = []
        while data.get(f'PRIMER_LEFT_{ i }_SEQUENCE'):
            primer_data = {
                k: v for k, v in data.items()
                if key_matches_index(i, k)
            }
            primers.append(Primer(i, primer_data, sequence_template))
            i += 1
        return primers


class Primer:
    """Holds information about a potential primer pair."""

    def __init__(self, ix, data, sequence_template):
        """Parse details from output string."""
        self.index = ix
        self.penalties = {
            'pair': data[f'PRIMER_PAIR_{ ix }_PENALTY'],
            'left': data[f'PRIMER_LEFT_{ ix }_PENALTY'],
            'right': data[f'PRIMER_RIGHT_{ ix }_PENALTY'],
        }
        self.left = {
            'penalty': float(data[f'PRIMER_LEFT_{ ix }_PENALTY']),
            'sequence': data[f'PRIMER_LEFT_{ ix }_SEQUENCE'],
            'start': int(data[f'PRIMER_LEFT_{ ix }'].split(',')[0]),
            'end': int(data[f'PRIMER_LEFT_{ ix }'].split(',')[0]
                       + data[f'PRIMER_LEFT_{ ix }'].split(',')[1]),
            'length': int(data[f'PRIMER_LEFT_{ ix }'].split(',')[1]),
            'tm': float(data[f'PRIMER_LEFT_{ ix }_TM']),
            'gc': float(data[f'PRIMER_LEFT_{ ix }_GC_PERCENT']),
            'self_dimer_any_th':
                float(data[f'PRIMER_LEFT_{ ix }_SELF_ANY_TH']),
            'self_dimer_end_th':
                float(data[f'PRIMER_LEFT_{ ix }_SELF_END_TH']),
            'hairpin_th': float(data[f'PRIMER_LEFT_{ ix }_HAIRPIN_TH']),
            'end_stability': float(data[f'PRIMER_LEFT_{ ix }_END_STABILITY']),
        }
        self.right = {
            'penalty': float(data[f'PRIMER_RIGHT_{ ix }_PENALTY']),
            'sequence': data[f'PRIMER_RIGHT_{ ix }_SEQUENCE'],
            'start': int(data[f'PRIMER_RIGHT_{ ix }'].split(',')[0]),
            'end': int(data[f'PRIMER_RIGHT_{ ix }'].split(',')[0]
                       + data[f'PRIMER_RIGHT_{ ix }'].split(',')[1]),
            'length': int(data[f'PRIMER_RIGHT_{ ix }'].split(',')[1]),
            'tm': float(data[f'PRIMER_RIGHT_{ ix }_TM']),
            'gc': float(data[f'PRIMER_RIGHT_{ ix }_GC_PERCENT']),
            'self_dimer_any_th':
                float(data[f'PRIMER_RIGHT_{ ix }_SELF_ANY_TH']),
            'self_dimer_end_th':
                float(data[f'PRIMER_RIGHT_{ ix }_SELF_END_TH']),
            'hairpin_th': float(data[f'PRIMER_RIGHT_{ ix }_HAIRPIN_TH']),
            'end_stability': float(data[f'PRIMER_RIGHT_{ ix }_END_STABILITY']),
        }
        self.amplicon = sequence_template[self.left['start']:self.right['end']]
        self.amplicon_bp = data[f'PRIMER_PAIR_{ ix }_PRODUCT_SIZE']
        self.complement_any_th = data[f'PRIMER_PAIR_{ ix }_COMPL_ANY_TH']
        self.complement_end_th = data[f'PRIMER_PAIR_{ ix }_COMPL_END_TH']


def parse_output(output):
    """Parse string output from primer3 into useful properties."""
    return [
        Iteration(x)
        for x in output.split('\n=\n')
        if x.startswith('SEQUENCE_ID')
    ]


if __name__ == '__main__':
    with open('primer3/example.out') as f:
        iterations = parse_output(f.read())
    probes = [
        ''.join([
            random.choice(['A', 'T', 'G', 'C'])
            for x in range(8)
        ])
        for i in range(20)
    ]
    pairs = [
        primer_pair for primer_pair in iterations[0].primers
        if [
            p for p in probes
            if p in primer_pair.amplicon
        ]
    ]
    print(
        f"{ len(pairs) } primer pairs found",
        f"for n={ len(probes) } probe library"
    )
