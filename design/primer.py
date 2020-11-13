"""A wrapper around the primer3 software."""

import os
import time
import string
import random
import subprocess
from django.conf import settings
from django.template.loader import render_to_string

import logging
logger = logging.getLogger('django')

COMPLEMENT = {
    'A': 'T',
    'T': 'A',
    'G': 'C',
    'C': 'G',
}

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
        self.total_assay_count = sum([
            len(iteration.assays)
            for iteration in self.iterations
        ])

    def __str__(self):
        """Render entire result to string."""
        out = []
        for i, query in enumerate(self.iterations):
            out.append(
                f"\nQuery #{i + 1}: {query.name}\n"
                + f"    - Considered {query.assays_considered} assays\n"
                + f"    - Rejected {query.assays_rejected} assays\n"
            )
            if settings.PRIMER3_DEBUG:
                out += [
                    str(assay).replace(
                        '<span class="green">', '').replace('</span>', '')
                    for assay in query.assays
                ]
        return '\n\n'.join(out)

    def __len__(self):
        """Return number of iterations."""
        return len(self.iterations)

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
            if not params['amplicon_min']:
                return

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
        if settings.PRIMER3_DEBUG:
            logger.info(
                'Running primer3 input: '
                + os.path.basename(input_path)
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
            raise RuntimeError(
                f"Primer3 returned error code {exc.returncode}. Output:"
                + '\n' + exc.stdout.decode('utf-8')
                + '\n' + exc.stderr.decode('utf-8')
            )
        clean_input_files(input_path)

        if settings.PRIMER3_DEBUG:
            out = os.path.join(
                settings.PRIMER3_OUTPUT_DIR,
                os.path.basename(input_path).replace('.conf', '.out')
            )
            with open(out, 'w') as f:
                f.write(result.stdout.decode('utf-8') + '\n')

        return [
            Iteration('SEQUENCE_ID=' + x)
            for x in result.stdout.decode('utf-8').split('SEQUENCE_ID=')[1:]
        ]


class Iteration:
    """Holds primer predictions for a single query sequence."""

    def __init__(self, output):
        """Parse iteration data from output string."""
        data = {
            line.split('=')[0]: line.split('=')[1]
            for line in output.split('\n')
            if '=' in line
        }
        self.assays_rejected = 0
        self.assays_considered = 0
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

        i = 0
        assays = []
        while data.get(f'PRIMER_LEFT_{ i }_SEQUENCE'):
            assay_data = {
                k: v for k, v in data.items()
                if key_matches_index(i, k)
            }
            builder = AssayBuilder(self, i, assay_data, sequence_template)
            assays += builder.build()
            i += 1

        return reduced(assays)

    def get_probe_ids(self):
        """Return unique list of probe IDs sorted numerically."""
        return [
            str(x)
            for x in sorted(
                list(
                    {
                        int(assay.probe['id'])
                        for assay in self.assays
                    }
                )
            )
        ]

    def get_probes_string(self):
        """Return string list of probe IDs."""
        probe_ids = self.get_probe_ids()
        if len(probe_ids) == 1:
            return "probe #" + probe_ids[0]
        elif len(probe_ids) > 1:
            return 'probes #' + ', #'.join(probe_ids)


class AssayBuilder:
    """A PCR assay with potentially multiple probe sites."""

    def __init__(self, parent, ix, data, sequence_template):
        """Parse details from output string."""
        self.query = parent
        self.index = ix + 1
        self.left = {
            'penalty': float(data[f'PRIMER_LEFT_{ ix }_PENALTY']),
            'sequence': data[f'PRIMER_LEFT_{ ix }_SEQUENCE'],
            'start': int(data[f'PRIMER_LEFT_{ ix }'].split(',')[0]),
            'end': (int(data[f'PRIMER_LEFT_{ ix }'].split(',')[0])
                    + int(data[f'PRIMER_LEFT_{ ix }'].split(',')[1])),
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
            'start': (int(data[f'PRIMER_RIGHT_{ ix }'].split(',')[0])
                      + 2 - int(data[f'PRIMER_RIGHT_{ ix }'].split(',')[1])),
            'end': int(data[f'PRIMER_RIGHT_{ ix }'].split(',')[0]) + 1,
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
            self.left['start']:(self.right['end'])
        ]
        self.amplicon_inner = self.amplicon[
            self.left['length']:(-1 * self.right['length'])
        ]
        self.probes = self.get_probes()

    def get_probes(self):
        """Match assay to UPL probes."""
        def get_distance(probe):
            """Return probe distance."""
            return probe['distance']

        def get_probe_distance(self, probe):
            """Return the minimum distance of probe from amplicon 5' or 3'."""
            inner_start = self.amplicon_inner.find(probe)
            inner_end = inner_start + len(probe)
            return min([
                inner_start,
                len(self.amplicon_inner) - inner_end
            ])

        def reverse_complement(sequence):
            """Return reverse complement of sequence."""
            return ''.join([
                COMPLEMENT[nt] for nt in sequence[::-1].upper()
            ])

        probes = []

        for probe_ix, probe_seq in settings.UPL_PROBES.items():
            for probe in [probe_seq, reverse_complement(probe_seq)]:
                if probe in self.amplicon_inner:
                    self.query.assays_considered += 1
                    probe_start = (
                        self.left['end']
                        + self.amplicon_inner.find(probe) + 1
                    )
                    distance = get_probe_distance(self, probe)
                    if distance < settings.MIN_PROBE_DISTANCE:
                        self.query.assays_rejected += 1
                        continue
                    if self.amplicon_inner.count(probe) > 1:
                        self.query.assays_rejected += 1
                        logger.info('Rejected assay: multiple probe sites')
                        continue
                    probes.append({
                        'id': probe_ix,
                        'sequence': probe,
                        'start': probe_start,
                        'end': probe_start + len(probe),
                        'distance': distance,
                    })
        return sorted(probes, key=get_distance, reverse=True)

    def build(self):
        """Return a list of assays generated from this build."""
        return [
                Assay(self, probe)
                for probe in self.probes
            ]


class Assay:
    """A PCR assay describing a set of primers and a probe."""

    def __init__(self, builder, probe):
        """Create the assay from the builder template."""
        self.probe = probe
        self.query = builder.query
        self.index = builder.index
        self.left = builder.left
        self.right = builder.right
        self.complement_any_th = builder.complement_any_th
        self.complement_end_th = builder.complement_end_th
        self.amplicon_bp = builder.amplicon_bp
        self.amplicon = builder.amplicon
        self.amplicon_inner = builder.amplicon_inner

    def __str__(self):
        """Return sequence alignment of the assay."""
        probe = self.probe
        query_start_ix = max(self.left['start'] - 10, 0)
        query_end_ix = min(
            self.right['end'] + 10,
            len(self.query.sequence) - 1
        )
        s1 = min(self.left['start'], 10)
        s2 = probe['start'] - self.left['end'] - 1
        s3 = self.right['start'] - probe['end']
        line2 = (
            " " * s1
            + self.left['sequence']
            + " " * s2
            + f'<span class="green">{probe["sequence"]}</span>'
            + " " * s3
            + self.right['sequence']
        )
        line1 = (
            " " * (line2.find(probe['sequence']) - 18)
            + f'<span class="green">#{probe["id"]}</span>'
        )
        line3 = self.query.sequence[query_start_ix:query_end_ix]
        line4 = (
            str(query_start_ix)
            + " " * (len(line3) - len(str(query_end_ix)))
            + str(query_end_ix)
        )
        return '\n'.join([line1, line2, line3, line4])


def clean_input_files(new_path):
    """Clean files from directory older than 1 hour."""
    for temp_dir in (settings.PRIMER3_INPUT_DIR, settings.PRIMER3_OUTPUT_DIR):
        for f in os.listdir(temp_dir):
            path = os.path.join(temp_dir, f)
            if time.time() - os.path.getmtime(path) > 3600:
                os.remove(path)


if __name__ == '__main__':
    def reverse_comp(sequence):
        """Return reverse complement of sequence."""
        COMP = {
            'A': 'T',
            'T': 'A',
            'G': 'C',
            'C': 'G',
        }
        return ''.join([
            COMP[nt] for nt in sequence[::-1].upper()
        ])

    print(reverse_comp('TCGATCGACACTAGCATTAGC'))
