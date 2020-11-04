"""A wrapper around the primer3 software."""

import os
import json
import string
import random
import subprocess
from django.conf import settings
from django.template.loader import render_to_string

import logging
logger = logging.getLogger('django')

PRODUCT_SIZE_RANGES = [
    (101, 200),
    (201, 300),
    (301, 400),
    (401, 500),
    (501, 600),
    (601, 700),
    (701, 850),
    (851, 1000),
    (1001, 1500),
    (1501, 3000),
    (3001, 5000),
    (5001, 7000),
    (7001, 10000),
    (10001, 20000),
]


class PrimerDesign:
    """Analyse a target DNA sequence with primer3 for potential primers.

    Cross-reference the amplicon sequence of potential primer pairs against
    the Roche UPL probe sequences to find assays with internal probe
    hybridization sites.
    """

    def __init__(self, params):
        """Run primer3 with the given target sequences and render output."""
        self.params = params
        self.iterations = self.run(params)
        self.filter_probe_assays()

    def __str__(self):
        """Render entire result to string."""
        out = []
        for i, query in enumerate(self.iterations):
            out.append(f"Query #{i + 1}: {query.name}\n")
            out += [str(assay) for assay in query.assays]
        return '\n\n'.join(out)

    def __iter__(self):
        """Iterate through result sequences."""
        self.ix = 0
        return self

    def __next__(self):
        """Return next sequence in iteration."""
        if self.ix < len(self.iterations):
            this = self.iterations[self.ix]
            self.ix += 1
            return this
        raise StopIteration

    def create_input(self, params):
        """Parse the target parameters to a primer3 input file."""
        def get_size_range(params):
            """Calculate valid Primer3 size range from amplicon min/max."""
            selected = []
            for size in PRODUCT_SIZE_RANGES:
                if params['amplicon_min'] > size[1]:
                    continue
                if params['amplicon_max'] < size[0]:
                    break
                selected.append('-'.join([str(x) for x in size]))
            return ' '.join(selected)

        alphanumeric = string.ascii_letters + string.digits
        input_path = os.path.join(
            settings.PRIMER3_INPUT_DIR,
            '%s.conf' % ''.join([
                random.choice(alphanumeric)
                for i in range(12)
            ])
        )
        logger.info(
            "Creating Primer3 input with FASTA:\n"
            + '\n\n'.join([
                f"Query: {k}\nSequence:{v}"
                for k, v in params['fasta'].items()
            ])
        )
        params['product_size_range'] = get_size_range(params)
        params['conf_path'] = settings.PRIMER3_CONFIG_PATH
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
        try:
            result = subprocess.run(args, check=True, capture_output=True)
        except Exception as exc:
            if exc.returncode == 252:
                # "PRIMER_ERROR=Missing SEQUENCE tag" ... don't know why
                result = exc
            else:
                raise RuntimeError(
                    f"Primer3 returned error code {exc.returncode}. Output:"
                    + '\n' + exc.stdout.decode('utf-8')
                    + '\n' + exc.stderr.decode('utf-8')
                )
        os.remove(input_path)
        return [
            Iteration(x)
            for x in result.stdout.decode('utf-8').split('\n=\n')
            if x.startswith('SEQUENCE_ID')
        ]

    def filter_probe_assays(self):
        """Cross-reference against UPL sequences to get probe assays."""
        def get_distance(probe):
            """Return probe distance."""
            return probe['distance']

        def get_probe_distance(sequence, start, assay):
            """Return the minimum distance of probe from amplicon 5' or 3'."""
            return min([
                start,
                len(assay.amplicon_inner) - start + len(sequence)
            ])

        def reduced(assays):
            """Return only 5 assays per probe."""
            reduced = []
            probe_count = {}
            for assay in assays:
                if not assay.probe:
                    continue
                probe_id = assay.probe['id']
                if probe_id not in probe_count:
                    probe_count[probe_id] = 1
                    reduced.append(assay)
                    continue
                if probe_count[probe_id] < 5:
                    probe_count[probe_id] += 1
                    reduced.append(assay)
            return reduced

        with open(settings.PROBE_SEQUENCE_PATH) as f:
            probes = json.load(f)

        for query in self.iterations:
            for assay in query.assays:
                for probe_ix, sequence in probes.items():
                    if sequence in assay.amplicon_inner:
                        start = assay.amplicon_inner.find(sequence)
                        distance = get_probe_distance(sequence, start, assay)
                        if distance < 5:
                            continue
                        assay.probes.append({
                            'id': probe_ix,
                            'sequence': sequence,
                            'start': start,
                            'end': start + len(sequence),
                            'distance': distance,
                        })
                if len(assay.probes) > 1:
                    assay.probes.sort(key=get_distance, reverse=True)
                if assay.probes:
                    assay.probe = assay.probes[0]
            query.assays = reduced(query.assays)


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
        self.assays = self.parse_assays(data, self.sequence)

    def parse_assays(self, data, sequence_template):
        """Parse primer pairs from output dict."""
        def key_matches_index(i, key):
            """Parse int index from key string."""
            try:
                return key.split('_')[2] == str(i)
            except IndexError:
                return False

        i = 0
        assays = []
        while data.get(f'PRIMER_LEFT_{ i }_SEQUENCE'):
            assay_data = {
                k: v for k, v in data.items()
                if key_matches_index(i, k)
            }
            assays.append(Assay(self, i, assay_data, sequence_template))
            i += 1

        return assays


class Assay:
    """Holds information about a potential primer pair."""

    def __init__(self, parent, ix, data, sequence_template):
        """Parse details from output string."""
        self.query = parent
        self.index = ix
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
        self.complement_any_th = data[f'PRIMER_PAIR_{ ix }_COMPL_ANY_TH']
        self.complement_end_th = data[f'PRIMER_PAIR_{ ix }_COMPL_END_TH']
        self.amplicon_bp = data[f'PRIMER_PAIR_{ ix }_PRODUCT_SIZE']
        self.amplicon = sequence_template[
            self.left['start']:(1 + self.right['end'])
        ]
        self.amplicon_inner = self.amplicon[
            self.left['length']:(-1 * self.right['length'])
        ]
        self.probe = {}
        self.probes = []

    def __str__(self):
        """Return sequence alignment of the assay."""
        if not self.probes:
            return (
                f"Primer left: {self.left['sequence']}"
                f"\nPrimer right: {self.right['sequence']}"
                f"\nAmplicon length: {self.amplicon_bp} nt"
                f"\nAmplicon: {self.amplicon}"
                "\nNo probes for this assay."
            )
        probe = self.probes[0]
        query_start_ix = max(self.left['start'] - 10, 0)
        query_end_ix = min(
            self.right['end'] + 10,
            len(self.query.sequence) - 1
        )
        line2 = (
            " " * 10
            + self.left['sequence']
            + " " * probe['start']
            + probe['sequence']
            + " " * (self.right['start'] - probe['end'])
            + self.right['sequence']
        )
        line1 = (
            " " * (line2.find(probe['sequence']) + 2)
            + '#' + probe['id']
        )
        line3 = self.query.sequence[query_start_ix:query_end_ix]
        line4 = (
            str(query_start_ix)
            + " " * (len(line3) - len(str(query_end_ix)))
            + str(query_end_ix)
        )
        return '\n'.join([line1, line2, line3, line4])


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
