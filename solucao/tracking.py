"""Registra no MLflow as execuções de results/ e o ciclo de vida do modelo oficial.

Cada pasta de execução vira um run com parâmetros, métricas, artefatos e o modelo.
A busca de cada janela e família de modelo vira um run filho. O modelo oficial é
cadastrado no Model Registry com o apelido "champion", e cada ciclo de
monitoramento vira um run ligado a essa versão.

Os arquivos de results/ continuam sendo a fonte da verdade: o MLflow é uma visão
sobre eles e pode ser recriado a qualquer momento apagando mlflow.db e mlartifacts/.
Rodar de novo só acrescenta o que ainda não foi registrado.

Uso: python tracking.py    e depois    mlflow ui --backend-store-uri sqlite:///mlflow.db
"""

import json
import os
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import joblib
import mlflow
from mlflow import MlflowClient
import mlflow.sklearn
import pandas as pd

from evaluation import REGISTRY, folder_hash
from monitoring import OFFICIAL_RUN
from tuning import RESULTS

TRACKING_URI = "sqlite:///mlflow.db"
ARTIFACTS = Path("mlartifacts").resolve().as_uri()
EXPERIMENT = "previsao-aih-dcnt"
MONITORING_EXPERIMENT = "monitoramento-modelo-oficial"
MODEL_NAME = "previsao-aih-dcnt-mlp"
MODEL_VERSION_TAG = "1.0.0"  # git tag modelo-v1.0.0
RUN_IDS = RESULTS / "mlflow_runs.csv"

# Máquinas das execuções anteriores ao registro automático em config.json.
DECLARED_MACHINES = {
    "20261105T205507": {"sistema": "Debian Linux", "processador": "AMD Ryzen 7 série 4000",
                        "fonte": "declarado pela equipe em 2026-11-23"},
    "20261118T221057": {"sistema": "macOS", "processador": "Apple M4",
                        "fonte": "máquina da reprodução de 2026-11-18"},
}


def machine_tag(folder, config):
    machine = config.get("machine") or DECLARED_MACHINES.get(folder.name, "não registrada na execução")
    return json.dumps(machine, ensure_ascii=False)


def experiment_id(name):
    found = mlflow.get_experiment_by_name(name)
    return found.experiment_id if found else mlflow.create_experiment(name, artifact_location=ARTIFACTS)


def already_logged(experiment, folder):
    runs = mlflow.search_runs([experiment], filter_string=f"tags.pasta = '{folder}'", output_format="list")
    return runs[0].info.run_id if runs else None


def overall_metrics(table, prefix):
    metrics = {}
    for row in table.itertuples():
        group = "geral" if row.group == "all" else row.group
        for name in ("mae", "rmse", "wape", "bias"):
            metrics[f"{prefix}_{name}_{group}"] = getattr(row, name)
        if group == "geral":
            metrics[f"{prefix}_macro_wape"] = row.macro_wape
    return metrics


def log_run(folder, registry_row, experiment):
    config = json.loads((folder / "config.json").read_text())
    best = json.loads((folder / "best_params.json").read_text())
    winner = min(best, key=lambda item: item["validation_macro_wape"])
    metrics = pd.read_csv(folder / "metrics.csv")
    official = folder.name == OFFICIAL_RUN.name

    with mlflow.start_run(experiment_id=experiment, run_name=folder.name) as run:
        mlflow.set_tags({
            "pasta": folder.name,
            "oficial": str(official).lower(),
            "papel": "modelo oficial da Etapa 4" if official else "reprodução em outra máquina",
            "data_avaliacao_utc": registry_row["date_utc"],
            "pasta_sha256": registry_row["folder_sha256"],
            "dataset_sha256": config["dataset_sha256"],
            "maquina": machine_tag(folder, config),
        })
        mlflow.log_params({
            "modelo": winner["model"],
            "janela_inicio": winner["window_start"],
            **{f"hp_{key}": value for key, value in winner["params"].items()},
            "semente": config["seed"],
            "trials_por_modelo": config["trials_per_model"],
            "janelas": ",".join(config["window_starts"]),
            "anos_validacao": ",".join(map(str, config["validation_years"])),
            "fim_desenvolvimento": config["development_end"],
            "features": len(config["features"]),
            **{f"versao_{key}": value for key, value in config["versions"].items()},
        })
        mlflow.log_metric("validacao_macro_wape", winner["validation_macro_wape"])
        mlflow.log_metrics(overall_metrics(metrics[metrics["method"] == winner["model"]], "teste"))
        mlflow.log_metrics(overall_metrics(metrics[metrics["method"] == "baseline"], "baseline"))
        for name in ("config.json", "best_params.json", "trials.csv", "metrics.csv", "predictions.csv", "model.joblib"):
            mlflow.log_artifact(str(folder / name), artifact_path="execucao")

        # One child run per window and model family: the search behind the winner.
        for item in best:
            with mlflow.start_run(experiment_id=experiment, run_name=f"busca {item['window_start']} {item['model']}",
                                  nested=True):
                mlflow.set_tags({"pasta": f"{folder.name}/busca", "tipo": "busca"})
                mlflow.log_params({"modelo": item["model"], "janela_inicio": item["window_start"],
                                   **{f"hp_{k}": v for k, v in item["params"].items()}})
                mlflow.log_metric("validacao_macro_wape", item["validation_macro_wape"])

        # The pickled model is loaded only after its folder hash matches the registry.
        assert folder_hash(folder) == registry_row["folder_sha256"], f"{folder} changed after evaluation"
        model = joblib.load(folder / "model.joblib")
        info = mlflow.sklearn.log_model(model, name="modelo", serialization_format="pickle")
        return run.info.run_id, info.model_uri


def register_official(model_uri, run_id):
    client = MlflowClient()
    existing = client.search_model_versions(f"name = '{MODEL_NAME}'")
    if any(version.run_id == run_id for version in existing):
        return next(version.version for version in existing if version.run_id == run_id)
    version = mlflow.register_model(model_uri, MODEL_NAME, tags={
        "versao_semantica": MODEL_VERSION_TAG,
        "tag_git": f"modelo-v{MODEL_VERSION_TAG}",
        "execucao": OFFICIAL_RUN.name,
    })
    client.update_registered_model(MODEL_NAME, description=(
        "MLP que prevê, um mês à frente, as AIHs iniciais de quatro grupos DCNT nos estabelecimentos do Paraná. "
        "Documentação: solucao/docs/model_card.md"))
    client.update_model_version(MODEL_NAME, version.version, description=(
        "Execução entregue na Etapa 3 (20261105T205507). Teste 2025: macro-WAPE 5,78%, WAPE 3,98%."))
    client.set_registered_model_alias(MODEL_NAME, "champion", version.version)
    return version.version


def log_monitoring(folder, experiment, model_version):
    summary = json.loads((folder / "summary.json").read_text())
    performance = pd.read_csv(folder / "performance.csv")
    drift = pd.read_csv(folder / "drift.csv")
    forecast = pd.read_csv(folder / "forecast.csv")
    levels = summary["scenarios"]["real_2026"]["levels"]

    with mlflow.start_run(experiment_id=experiment, run_name=folder.name) as run:
        mlflow.set_tags({
            "pasta": folder.name,
            "modelo": f"{MODEL_NAME} v{model_version}",
            "execucao_oficial": summary["official_run"],
            "nivel_geral": summary["scenarios"]["real_2026"]["overall"],
            **{f"nivel_{key}": value for key, value in levels.items()},
            **({"revisao": summary["revision"], "substitui": summary["replaces"],
                "avaliacao": summary["evaluation"]} if "revision" in summary else {}),
        })
        mlflow.log_params({"lote_inicio": summary["batch"]["start"], "lote_fim": summary["batch"]["end"],
                           "ultima_competencia": summary["batch"]["last_file"],
                           "meses_maduros": ",".join(summary["batch"]["mature_months"])})
        metrics = {"meses_maduros": len(summary["batch"]["mature_months"]),
                   "reconciliacao_maior_diferenca": summary["reconciliation"]["maior_diferenca_percentual"]}
        for row in performance.itertuples():
            group = "geral" if row.grupo == "all" else row.grupo
            metrics[f"{row.metodo}_wape_{group}"] = row.wape
            if group == "geral":
                metrics[f"{row.metodo}_macro_wape"] = row.macro_wape
            elif row.metodo == "mlp":
                metrics[f"mlp_vies_relativo_{group}"] = row.vies_relativo
        for row in drift.itertuples():
            metrics[f"drift_{row.indicador}"] = row.psi if pd.notna(row.psi) else row.media_atual
        for row in forecast.itertuples():
            metrics[f"previsao_diferenca_sem_correcao_{row.grupo_dcnt}"] = row.diferenca_percentual
        mlflow.log_metrics(metrics)
        mlflow.log_artifacts(str(folder), artifact_path="monitoramento")

    client = MlflowClient()
    client.set_model_version_tag(MODEL_NAME, model_version, f"monitoramento_{summary['batch']['last_file']}",
                                 summary["scenarios"]["real_2026"]["overall"])
    return run.info.run_id


def log_realtime(folder, experiment, model_version):
    """Error of the official model with forecasts issued one month ahead, without future data."""
    summary = json.loads((folder / "summary.json").read_text())
    with mlflow.start_run(experiment_id=experiment, run_name=folder.name) as run:
        mlflow.set_tags({"pasta": folder.name, "tipo": "avaliacao_tempo_real",
                         "modelo": f"{MODEL_NAME} v{model_version}", "execucao_oficial": summary["official_run"],
                         "regra": summary["rule"]})
        mlflow.log_params({"ultima_competencia": summary["last_file"],
                           **{f"meses_{period}": ",".join(months)
                              for period, months in summary["evaluated_months"].items()}})
        mlflow.log_metrics({f"macro_wape_{key.replace('/', '_')}": value for key, value in summary["macro_wape"].items()})
        mlflow.log_artifacts(str(folder), artifact_path="tempo_real")
    MlflowClient().set_model_version_tag(
        MODEL_NAME, model_version, "teste_2025_tempo_real_macro_wape",
        f"{summary['macro_wape']['teste_2025/com_correcao/mlp']:.2f}")
    return run.info.run_id


def main():
    mlflow.set_tracking_uri(TRACKING_URI)
    experiment = experiment_id(EXPERIMENT)
    registry = pd.read_csv(REGISTRY).set_index("run")
    rows = []

    for folder in sorted(path for path in RESULTS.iterdir() if path.is_dir() and path.name[:8].isdigit()):
        if not (folder / "metrics.csv").exists():
            continue
        run_id = already_logged(experiment, folder.name)
        if run_id is None:
            run_id, model_uri = log_run(folder, registry.loc[folder.name], experiment)
        else:
            model_uri = f"runs:/{run_id}/modelo"
            config = json.loads((folder / "config.json").read_text())
            MlflowClient().set_tag(run_id, "maquina", machine_tag(folder, config))
        rows.append({"tipo": "execucao", "pasta": folder.name, "run_id": run_id})
        if folder.name == OFFICIAL_RUN.name:
            version = register_official(model_uri, run_id)

    monitoring = experiment_id(MONITORING_EXPERIMENT)
    for folder in sorted(RESULTS.glob("monitoring_*")):
        run_id = already_logged(monitoring, folder.name) or log_monitoring(folder, monitoring, version)
        rows.append({"tipo": "monitoramento", "pasta": folder.name, "run_id": run_id})
    for folder in sorted(RESULTS.glob("realtime_*")):
        run_id = already_logged(monitoring, folder.name) or log_realtime(folder, monitoring, version)
        rows.append({"tipo": "tempo_real", "pasta": folder.name, "run_id": run_id})

    pd.DataFrame(rows).to_csv(RUN_IDS, index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"Model Registry: {MODEL_NAME} versão {version} com o apelido 'champion'")


if __name__ == "__main__":
    main()
