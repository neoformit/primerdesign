"""Read fasta sequence string into a useful object."""

from django.core.exceptions import ValidationError

import logging
logger = logging.getLogger('django')

DNA = {'A', 'T', 'G', 'C'}


def valid_dna(title, residue, sequence):
    """Assert that sequence string is valid DNA."""
    if len(set(sequence) - DNA):
        invalid = list(set(sequence) - DNA)[0]
        position = residue + sequence.index(invalid) + 1
        msg = (
            f'Sequence "{title}": Invalid DNA residue "{invalid}"'
            + f' at position {position}'
        )
        logger.info(f"FASTA failed form validation:\n{msg}")
        raise ValidationError({'fasta': msg})
    return True


class Fasta:
    """Parse fasta string and validate sequence."""

    def __init__(self, data):
        """Read in FASTA sequences as dict."""
        self.sequences = data
        self.index = list(data.keys())

    def __str__(self):
        """Convert FASTA object to fasta-formatted string."""
        writeList = []

        for title, sequence in self.items():
            seqList = []
            while True:
                if len(sequence) >= 80:
                    seqList.append(sequence[0:80])
                    sequence = sequence[80:]
                else:
                    seqList.append(sequence)
                    break
            writeList.append('>' + title + '\n' + '\n'.join(seqList))

        return '\n'.join(writeList)

    def __iter__(self):
        """Iterate through result sequences."""
        self.ix = 0
        return self

    def __next__(self):
        """Return next sequence in iteration."""
        if self.ix < len(self.index):
            this = self.sequences[self.index[self.ix]]
            self.ix += 1
            return this
        raise StopIteration

    def __getitem___(self, ix):
        """Return sequence at index."""
        return self.sequences[ix]

    def __setitem___(self, ix, value):
        """Set sequence at index."""
        self.sequences[ix] = value

    def keys(self):
        """Return index."""
        return set(self.index)

    def values(self):
        """Return sequences."""
        return self.sequences.values()

    def items(self):
        """Return tuple of (index, sequence)."""
        return self.sequences.items()

    @classmethod
    def from_string(Cls, string):
        """Read in from string and parse to dict."""
        residue = 0
        seq = ""
        title = ""
        fas = {}
        copy = False

        if '>' not in string:
            # Not FASTA formatted. Parse as single sequence.
            residue = 0
            title = "Anonymous sequence"
            seq = string.replace(' ', '').replace('\n', '').replace('\r', '')
            if valid_dna(title, residue, seq):
                fas[title] = seq.upper()
                return Cls(fas)

        for line in string.split('\n'):
            if line.startswith('>'):
                if copy:
                    fas[title] = seq.upper()
                title = line.strip(">\n\r ").replace(' ', '_')
                copy = True
                seq = ""
            else:
                line = line.strip("\n\r ")
                if valid_dna(title, residue, line):
                    seq += line
                    residue += len(line)

        # Ensure duplicate fasta titles don't get overwritten
        i = 1
        while f'{title}_{i}' in fas.keys():
            title = f'{title}_{i}'
            i += 1
        fas[title] = seq

        return Cls(fas)

if __name__ == '__main__':
    fasta_str = (
        '>part of X00351 Human mRNA for beta-actin\r\n'
        'CACGGCATCGTCACCAACTGGGACGACATGGAGAAAATCTGGCACCACACCTTCTACAATGAGCTGCGTGTGGCTCCCGA\r\n'
        'GGAGCACCCCGTGCTGCTGACCGAGGCCCCCCTGAACCCCAAGGCCAACCGCGAGAAGATGACCCAGATCATGTTTGAGA\r\n'
        'CCTTCAACACCCCAGCCATGTACGTTGCTATCCAGGCTGTGCTATCCCTGTACGCCTCTGGCCGTACCACTGGCATCGTG\r\n'
        'ATGGACTCCGGTGACGGGGTCACCCACACTGTGCCCATCTACGAGGGGTATGCCCTCCCC'
    )
    fas = Fasta.from_string(fasta_str)
    for key, seq in fas.items():
        assert seq in fasta_str.replace('\r\n', '')
    print(fas)
