from pathlib import Path
p = Path('main.py')
for i, l in enumerate(p.read_text().splitlines(), 1):
    if len(l) > 120:
        print(i, len(l), l)
