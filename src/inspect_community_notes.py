# python
import os
import sys
import pandas as pd

FNAME = "notes-00000.tsv"

if not os.path.exists(FNAME):
    print(f"Plik {FNAME} nie istnieje w bieżącym katalogu.")
    sys.exit(1)

# Wczytaj pierwsze 1000 wierszy jako stringi, aby porównanie było pewne
df = pd.read_csv(FNAME, sep="\t", nrows=1000, dtype=str)
col = "misleadingMissingImportantContext"
if col in df.columns:
    filtered = df[df[col] != "1"]
else:
    print(f"Kolumna `{col}` nie znaleziona — zwracam pierwsze 1000 wierszy bez filtrowania.")
    filtered = df
# Wyświetl wynik jako TSV bez indeksu
print(filtered.to_csv(sep="\t", index=False))
