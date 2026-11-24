"""Avalia em 2025 o modelo vencedor da busca, comparando-o com a referência sazonal.

Salva o modelo, as métricas e as previsões na pasta da execução e depois registra o
hash dessa pasta em results/registry.csv. A data e o hash ficam fora da pasta, para
que dois experimentos idênticos gerem o mesmo hash.

Uso: python evaluation.py [results/<execução>]    (padrão: a execução mais recente)
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

import joblib
import pandas as pd

from tuning import DATASET, DEVELOPMENT_END, RESULTS, TARGET, between, content_hash, file_hash, macro_wape, predict, train

TEST_START, TEST_END = "2025-01", "2025-12"
REGISTRY = RESULTS / "registry.csv"


def metrics(rows, predicted):
    errors = predicted - rows[TARGET]
    return {
        "mae": errors.abs().mean(),
        "rmse": (errors ** 2).mean() ** 0.5,
        "wape": 100 * errors.abs().sum() / rows[TARGET].sum(),
        "bias": errors.mean(),
    }


def metrics_table(rows, predictions):
    table = []
    for method, predicted in predictions.items():
        table.append({"method": method, "group": "all", "macro_wape": macro_wape(rows, predicted),
                      **metrics(rows, predicted)})
        for group, group_rows in rows.groupby("grupo_dcnt"):
            table.append({"method": method, "group": group, **metrics(group_rows, predicted[group_rows.index])})
    return pd.DataFrame(table)


def folder_hash(folder):
    digest = sha256()
    for path in sorted(folder.iterdir()):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    runs = [path for path in RESULTS.iterdir() if path.is_dir() and path.name[:8].isdigit()]  # skip monitoring_*
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else max(runs)
    assert not (run / "metrics.csv").exists(), f"{run} was already evaluated"

    config = json.loads((run / "config.json").read_text())
    if file_hash(DATASET) != config["dataset_sha256"]:
        # Same values can be written with different bytes on another machine; compare the content then.
        assert content_hash(DATASET) == config.get("dataset_content_sha256"), "the dataset changed after tuning"
        print("Dataset file hash differs, but its content is the same as in tuning.")

    best = json.loads((run / "best_params.json").read_text())
    winner = min(best, key=lambda item: item["validation_macro_wape"])
    params = winner["params"]
    if "hidden_layer_sizes" in params:
        params["hidden_layer_sizes"] = tuple(params["hidden_layer_sizes"])

    data = pd.read_parquet(DATASET)
    development = between(data, winner["window_start"], DEVELOPMENT_END)
    test = between(data, TEST_START, TEST_END)

    model = train(winner["model"], params, development)
    predictions = {
        winner["model"]: predict(model, test),
        "baseline": test["lag_12"].astype(float),  # same group, same month of the previous year
    }
    table = metrics_table(test, predictions)

    joblib.dump(model, run / "model.joblib")
    table.to_csv(run / "metrics.csv", index=False)
    test[["mes_internacao", "grupo_dcnt", TARGET]].assign(**predictions).to_csv(run / "predictions.csv", index=False)

    overall = table[(table["method"] == winner["model"]) & (table["group"] == "all")].iloc[0]
    entry = {
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run": run.name,
        "folder_sha256": folder_hash(run),
        "dataset_sha256": config["dataset_sha256"],
        "model": winner["model"],
        "window_start": winner["window_start"],
        "validation_macro_wape": winner["validation_macro_wape"],
        "test_macro_wape": overall["macro_wape"],
        "test_wape": overall["wape"],
    }
    pd.DataFrame([entry]).to_csv(REGISTRY, mode="a", header=not REGISTRY.exists(), index=False)
    print(table.round(2).to_string(index=False))
    print(f"\nFolder hash: {entry['folder_sha256']}")


if __name__ == "__main__":
    main()
