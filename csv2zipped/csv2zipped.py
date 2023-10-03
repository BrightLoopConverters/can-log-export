import pandas as pd
import os
from pathlib import Path
import shutil

datadir = Path(__file__).parent.parent / 'data'
filename = "<filename>.csv"
filepath = datadir / filename

if os.path.exists(filename):
    shutil.rmtree(filename)
os.mkdir(filename)
print('> Created directory: ', filename)

df_iter = pd.read_csv(filepath, delimiter=';', decimal=',', nrows=200000,
                      encoding='latin-1', chunksize=1e3)

df = pd.DataFrame()
for chunk in df_iter:
    df = pd.concat([df, chunk])

used_signals = []
df_groups = []

N_group = 0

for signal in df.keys()[1:]:
    # skip time
    if signal in used_signals:
        continue
    clean_signal = df[signal].dropna()
    df_group = df.loc[clean_signal.index].dropna(axis=1, how='all')
    df_groups.append(df_group)
    used_signals += list(df_group.keys())
    outputCsv = os.path.join(filename, f'group_{N_group}.csv')
    df_group.to_csv(outputCsv)
    N_group += 1
    print('Created CSV file: ', outputCsv)

# make zip
zip_file_name = shutil.make_archive(filename, 'zip', filename)
print('Created ZIP file: ', zip_file_name)