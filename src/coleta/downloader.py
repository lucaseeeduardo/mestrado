import enum
import io
import os
import time
import zipfile

import pandas as pd
import requests
from sqlalchemy import Column, Date, Float, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import declarative_base, sessionmaker

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.config import CURRENCY_SCALE_MAP

Base = declarative_base()

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent.parent / "data")))


class DRE(Base):
    __tablename__ = "dre"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cnpj_cia = Column(String)
    dt_refer = Column(Date)
    versao = Column(Integer)
    denom_cia = Column(String)
    cd_cvm = Column(String)
    grupo_dfp = Column(String)
    moeda = Column(String)
    escala_moeda = Column(String)
    ordem_exerc = Column(String)
    dt_ini_exerc = Column(Date)
    dt_fim_exerc = Column(Date)
    cd_conta = Column(String)
    ds_conta = Column(String)
    vl_conta = Column(Float)
    st_conta_fixa = Column(String)
    vl_formatado = Column(Float)

    __table_args__ = (
        UniqueConstraint("cnpj_cia", "dt_refer", "cd_conta", "ordem_exerc", name="unique_dre_record"),
    )


class DS_COLUMNS(enum.Enum):
    CNPJ_CIA = "CNPJ_CIA"
    DT_REFER = "DT_REFER"
    DT_INI_EXERC = "DT_INI_EXERC"
    DT_FIM_EXERC = "DT_FIM_EXERC"
    VL_CONTA = "VL_CONTA"
    ESCALA_MOEDA = "ESCALA_MOEDA"
    VL_FORMATADO = "VL_FORMATADO"
    VERSAO = "VERSAO"
    MOEDA = "MOEDA"


def post_dre_by_date(anos, session):
    for ano in anos:
        url = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"
        print(f"--- Processando ano: {ano} ---")
        try:
            response = requests.get(url, timeout=60 * 5)
            if response.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    with z.open(f"dfp_cia_aberta_DRE_con_{ano}.csv") as f:
                        df = pd.read_csv(f, encoding="latin1", sep=";", low_memory=False, decimal=".")
                        df[DS_COLUMNS.VL_FORMATADO.value] = (
                            df[DS_COLUMNS.VL_CONTA.value] * df[DS_COLUMNS.ESCALA_MOEDA.value].map(CURRENCY_SCALE_MAP)
                        )
                        insert_df_to_db(df, session)
            else:
                print(f"Erro {response.status_code} para o ano {ano}")
        except Exception as e:
            print(f"Falha ao baixar {ano}: {e}")
        time.sleep(1)


def insert_df_to_db(df, session):
    records = [
        {
            "cnpj_cia": row["CNPJ_CIA"],
            "dt_refer": pd.to_datetime(row["DT_REFER"]).date(),
            "versao": int(row["VERSAO"]),
            "denom_cia": row["DENOM_CIA"],
            "cd_cvm": row["CD_CVM"],
            "grupo_dfp": row["GRUPO_DFP"],
            "moeda": row["MOEDA"],
            "escala_moeda": row["ESCALA_MOEDA"],
            "ordem_exerc": row["ORDEM_EXERC"],
            "dt_ini_exerc": pd.to_datetime(row["DT_INI_EXERC"]).date(),
            "dt_fim_exerc": pd.to_datetime(row["DT_FIM_EXERC"]).date(),
            "cd_conta": row["CD_CONTA"],
            "ds_conta": row["DS_CONTA"],
            "vl_conta": float(row["VL_CONTA"]),
            "st_conta_fixa": row["ST_CONTA_FIXA"],
            "vl_formatado": float(row["VL_FORMATADO"]),
        }
        for _, row in df.iterrows()
    ]
    stmt = pg_insert(DRE.__table__).values(records)
    stmt = stmt.on_conflict_do_nothing(index_elements=["cnpj_cia", "dt_refer", "cd_conta", "ordem_exerc"])
    session.execute(stmt)
    session.commit()
    print(f"Processados {len(records)} registros (duplicatas ignoradas).")


def process_local_csvs(session):
    import glob as _glob
    csv_files = _glob.glob(str(DATA_DIR / "dfp_cia_aberta_DRE_con_*.csv"))
    for csv_file in csv_files:
        print(f"Processando {csv_file}")
        df = pd.read_csv(csv_file, encoding="latin1", sep=";", low_memory=False, decimal=".")
        df[DS_COLUMNS.VL_FORMATADO.value] = (
            df[DS_COLUMNS.VL_CONTA.value] * df[DS_COLUMNS.ESCALA_MOEDA.value].map(CURRENCY_SCALE_MAP)
        )
        insert_df_to_db(df, session)


if __name__ == "__main__":
    database_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/dre_db")
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    process_local_csvs(session)

    anos = list(range(2018, 2026))
    post_dre_by_date(anos, session)

    session.close()
