#!/usr/bin/env python3

import json


def reverse_complement(sequence):
    """Return reverse complement of sequence."""
    return ''.join([
        COMPLEMENT[nt] for nt in sequence[::-1].upper()
    ])


COMPLEMENT = {
    'A': 'T',
    'T': 'A',
    'G': 'C',
    'C': 'G',
}



with open('roche_upl_sequences.json') as f:
    probes = json.load(f)

print()
found = False
query = input('Paste query sequence and press enter:\n> ')
query = query.strip().replace('\n', '').replace('\r', '')
print()

for ix, probe in probes.items():
    if probe in query:
        found = True
        print(f"Found probe #{ix}: {probe}")
    elif reverse_complement(probe) in query:
        found = True
        print(f"Found probe #{ix}: {probe}")

if not found:
    print("No matching probes, sorry!")
print()

