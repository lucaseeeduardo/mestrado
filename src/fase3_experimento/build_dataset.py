"""
Fase 3 — Construção do dataset de desambiguação

Para cada empresa/exercício na base CVM, monta um 'puzzle':
  - contas: lista de DS_CONTA de nível 1 do DRE (sem CD_CONTA)
  - receita_bruta_gt: DS_CONTA que corresponde a CD_CONTA=3.01
  - vl_receita_bruta: valor em reais do campo correto

Salva como JSONL para ser consumido pelo pipeline de experimento.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.config import NIVEL1_PATTERN, ORDEM_EXERC, RECEITA_BRUTA_CODIGO
from src.utils.cvm_loader import carregar_todos_csvs

OUT_DIR = Path(__file__).parent.parent.parent / "output" / "fase3"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def construir_puzzles(df: pd.DataFrame) -> list[dict]:
    nivel1 = df[
        df["CD_CONTA"].str.match(NIVEL1_PATTERN, na=False)
        & (df["ORDEM_EXERC"] == ORDEM_EXERC)
    ].copy()

    puzzles = []
    chave = ["CNPJ_CIA", "DT_REFER", "DENOM_CIA"]

    for (cnpj, dt_refer, nome), grupo in nivel1.groupby(chave):
        rb_rows = grupo[grupo["CD_CONTA"] == RECEITA_BRUTA_CODIGO]
        if rb_rows.empty:
            # empresa sem conta 3.01 — estrutura atípica, ignorar
            continue

        rb_row = rb_rows.iloc[0]
        contas = grupo[["CD_CONTA", "DS_CONTA", "VL_FORMATADO"]].to_dict(orient="records")

        puzzles.append({
            "cnpj": cnpj,
            "dt_refer": dt_refer,
            "empresa": nome,
            "contas_ds": [c["DS_CONTA"] for c in contas],
            "receita_bruta_gt": rb_row["DS_CONTA"],
            "vl_receita_bruta": rb_row["VL_FORMATADO"],
            "_contas_completas": contas,
        })

    return puzzles


def main():
    print("Carregando CSVs...")
    df = carregar_todos_csvs()

    print("Construindo puzzles...")
    puzzles = construir_puzzles(df)

    out_path = OUT_DIR / "dataset_disambiguacao.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for p in puzzles:
            f.write(json.dumps(p, ensure_ascii=False, default=str) + "\n")

    gt_counts: dict[str, int] = {}
    for p in puzzles:
        gt = p["receita_bruta_gt"]
        gt_counts[gt] = gt_counts.get(gt, 0) + 1

    print(f"\nTotal de puzzles: {len(puzzles):,}")
    print("\nDistribuição dos GT (DS_CONTA de 3.01):")
    for ds, n in sorted(gt_counts.items(), key=lambda x: -x[1]):
        print(f"  {n:5d}  {ds}")
    print(f"\nDataset salvo em {out_path}")


if __name__ == "__main__":
    main()
