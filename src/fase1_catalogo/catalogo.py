"""
Fase 1 — Catálogo de variabilidade terminológica

Carrega os CSVs anuais da CVM, identifica todos os DS_CONTA associados
a CD_CONTA=3.01 (Receita Bruta) e aos códigos adjacentes (confundidores),
e salva os resultados para uso na modelagem da ontologia.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.config import NIVEL1_PATTERN, ORDEM_EXERC, RECEITA_BRUTA_CODIGO
from src.utils.cvm_loader import carregar_todos_csvs

OUT_DIR = Path(__file__).parent.parent.parent / "output" / "fase1"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def catalogar_sinonimos(df: pd.DataFrame) -> pd.DataFrame:
    """DS_CONTA únicos para CD_CONTA=3.01, com frequência e lista de anos."""
    rb = df[(df["CD_CONTA"] == RECEITA_BRUTA_CODIGO) & (df["ORDEM_EXERC"] == ORDEM_EXERC)].copy()
    return (
        rb.groupby("DS_CONTA")
        .agg(
            frequencia=("CNPJ_CIA", "count"),
            empresas_unicas=("CNPJ_CIA", "nunique"),
            anos=("DT_REFER", lambda x: sorted(x.str[:4].unique().tolist())),
        )
        .reset_index()
        .sort_values("frequencia", ascending=False)
    )


def catalogar_confundidores(df: pd.DataFrame) -> pd.DataFrame:
    """
    DS_CONTA de contas adjacentes (3.02, 3.03, …) que podem ser confundidas
    com Receita Bruta por correspondência léxica superficial.
    """
    nivel1 = df[
        df["CD_CONTA"].str.match(NIVEL1_PATTERN, na=False)
        & (df["ORDEM_EXERC"] == ORDEM_EXERC)
        & (df["CD_CONTA"] != RECEITA_BRUTA_CODIGO)
    ].copy()
    return (
        nivel1.groupby(["CD_CONTA", "DS_CONTA"])
        .agg(frequencia=("CNPJ_CIA", "count"))
        .reset_index()
        .sort_values(["CD_CONTA", "frequencia"], ascending=[True, False])
    )


def construir_dicionario_ontologia(sinonimos: pd.DataFrame) -> dict:
    """Estrutura pronta para alimentar a ontologia OWL."""
    return {
        "conceito_canonico": "ReceitaBruta",
        "codigo_cvm": RECEITA_BRUTA_CODIGO,
        "sinonimos": sinonimos["DS_CONTA"].tolist(),
        "total_ocorrencias": int(sinonimos["frequencia"].sum()),
        "empresas_unicas": int(sinonimos["empresas_unicas"].sum()),
    }


def main():
    df = carregar_todos_csvs()

    sinonimos = catalogar_sinonimos(df)
    confundidores = catalogar_confundidores(df)
    ontologia_dict = construir_dicionario_ontologia(sinonimos)

    sinonimos.to_csv(OUT_DIR / "sinonimos_receita_bruta.csv", index=False)
    confundidores.to_csv(OUT_DIR / "confundidores.csv", index=False)
    with open(OUT_DIR / "ontologia_base.json", "w", encoding="utf-8") as f:
        json.dump(ontologia_dict, f, ensure_ascii=False, indent=2)

    print("\n=== SINÔNIMOS DE RECEITA BRUTA (CD_CONTA=3.01) ===")
    print(sinonimos.to_string(index=False))
    print("\n=== CONFUNDIDORES (contas adjacentes) ===")
    print(confundidores.groupby("CD_CONTA").head(2).to_string(index=False))
    print(f"\nArquivos salvos em {OUT_DIR}")


if __name__ == "__main__":
    main()
