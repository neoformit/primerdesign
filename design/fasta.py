"""Read fasta sequence string into a useful object."""


class Fasta:
    """Parse fasta string and validate sequence."""

    def __init__(self, data):
        """Read in FASTSA sequences as dict."""
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
        seq = ""
        title = ""
        fas = {}
        copy = False

        for line in string.split('\n'):
            if line.startswith('>'):
                if copy:
                    fas[title] = seq
                title = line.strip(">\n\r ")
                copy = True
                seq = ""
            else:
                seq += line.strip("\n\r ")

        # Ensure duplicate fasta titles don't get overwritten
        i = 1
        while f'{title}_{i}' in fas.keys():
            title = f'{title}_{i}'
            i += 1
        fas[title] = seq

        return Cls(fas)
