import glob
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def carregar_todos_csvs() -> pd.DataFrame:
    arquivos = glob.glob(str(DATA_DIR / "dre_*" / "dre_*.csv"))
    frames = [pd.read_csv(f, sep=",", low_memory=False) for f in sorted(arquivos)]
    df = pd.concat(frames, ignore_index=True)
    print(f"Total de registros carregados: {len(df):,}")
    return df
