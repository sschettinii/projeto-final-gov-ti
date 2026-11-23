"""Busca os melhores hiperparâmetros de nove modelos em três janelas de histórico.

Cada modelo é validado em 2022, 2023 e 2024, sempre treinando com os meses anteriores.
O ano de teste (2025) nunca é usado aqui. Os resultados vão para uma nova pasta em results/.
"""

from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import platform
import warnings

import optuna
import pandas as pd
import sklearn
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import (
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import ElasticNet, PoissonRegressor, Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

DATASET = Path("data/modelagem_dcnt_mensal_201001_202512.parquet")
RESULTS = Path("results")

SEED = 42
TRIALS_PER_MODEL = 25
WINDOW_STARTS = ["2020-01", "2015-01", "2010-01"]
VALIDATION_YEARS = [2022, 2023, 2024]
DEVELOPMENT_END = "2024-12"

TARGET = "aih_iniciais"
FEATURES = [
    "grupo_dcnt", "mes_numero", "mes_seno", "mes_cosseno", "indice_temporal",
    "lag_1", "lag_2", "lag_3", "lag_6", "lag_12",
    "media_movel_3", "media_movel_6", "media_movel_12", "variacao_anual",
]

MODELS = {
    "random_forest": RandomForestRegressor,
    "extra_trees": ExtraTreesRegressor,
    "gradient_boosting": GradientBoostingRegressor,
    "hist_gradient_boosting": HistGradientBoostingRegressor,
    "ridge": Ridge,
    "poisson": PoissonRegressor,
    "elastic_net": ElasticNet,
    "svr_rbf": SVR,
    "mlp": MLPRegressor,
}
SCALE_INPUTS = {"ridge", "poisson", "elastic_net", "svr_rbf", "mlp"}
SCALE_TARGET = {"elastic_net", "svr_rbf", "mlp"}
MLP_LAYERS = {"8": (8,), "16": (16,), "32": (32,), "16x8": (16, 8), "32x16": (32, 16)}


def suggest_params(trial, name):
    if name in ("random_forest", "extra_trees"):
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 400, step=50),
            "max_depth": trial.suggest_categorical("max_depth", [6, 10, 14, 18, None]),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 8),
            "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", 0.7, 1.0]),
            "random_state": SEED,
            "n_jobs": -1,
        }
    if name == "gradient_boosting":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 50, 350, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "max_depth": trial.suggest_int("max_depth", 2, 5),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 8),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "random_state": SEED,
        }
    if name == "hist_gradient_boosting":
        return {
            "max_iter": trial.suggest_int("max_iter", 100, 400, step=50),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "max_leaf_nodes": trial.suggest_int("max_leaf_nodes", 7, 31),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 5, 30),
            "l2_regularization": trial.suggest_float("l2_regularization", 1e-5, 10.0, log=True),
            "random_state": SEED,
        }
    if name == "ridge":
        return {"alpha": trial.suggest_float("alpha", 1e-4, 1e4, log=True)}
    if name == "poisson":
        return {"alpha": trial.suggest_float("alpha", 1e-5, 1e2, log=True), "max_iter": 2000}
    if name == "elastic_net":
        return {
            "alpha": trial.suggest_float("alpha", 1e-4, 1e2, log=True),
            "l1_ratio": trial.suggest_float("l1_ratio", 0.0, 1.0),
            "max_iter": 10000,
            "random_state": SEED,
        }
    if name == "svr_rbf":
        return {
            "C": trial.suggest_float("C", 1e-2, 1e3, log=True),
            "epsilon": trial.suggest_float("epsilon", 1e-3, 1.0, log=True),
            "gamma": trial.suggest_float("gamma", 1e-4, 1.0, log=True),
            "kernel": "rbf",
        }
    if name == "mlp":
        return {
            "hidden_layer_sizes": MLP_LAYERS[trial.suggest_categorical("hidden_layer_sizes", list(MLP_LAYERS))],
            "activation": trial.suggest_categorical("activation", ["relu", "tanh"]),
            "solver": trial.suggest_categorical("solver", ["lbfgs", "adam"]),
            "alpha": trial.suggest_float("alpha", 1e-5, 1e1, log=True),
            "learning_rate_init": trial.suggest_float("learning_rate_init", 1e-4, 5e-2, log=True),
            "max_iter": 3000,
            "random_state": SEED,
        }
    raise ValueError(f"unknown model: {name}")


def build_model(name, params):
    estimator = MODELS[name](**params)
    if name in SCALE_TARGET:
        estimator = TransformedTargetRegressor(regressor=estimator, transformer=StandardScaler())
    steps = [("vetorizador", DictVectorizer(sparse=False))]
    if name in SCALE_INPUTS:
        steps.append(("escala", StandardScaler()))
    steps.append(("modelo", estimator))
    return Pipeline(steps)


def records(rows):
    return rows[FEATURES].to_dict("records")


def train(name, params, rows):
    return build_model(name, params).fit(records(rows), rows[TARGET].tolist())


def predict(model, rows):
    return pd.Series(model.predict(records(rows)), index=rows.index).clip(lower=0)


def macro_wape(rows, predicted):
    """Average the percentage error of each group, so that small groups count equally."""
    errors = (predicted - rows[TARGET]).abs().groupby(rows["grupo_dcnt"]).sum()
    totals = rows[TARGET].groupby(rows["grupo_dcnt"]).sum()
    return 100 * (errors / totals).mean()


def between(data, start, end):
    return data[data["mes_internacao"].between(start, end)]


def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()


def tune(name, development):
    folds = [
        (development[development["mes_internacao"] < f"{year}-01"],
         between(development, f"{year}-01", f"{year}-12"))
        for year in VALIDATION_YEARS
    ]

    def objective(trial):
        params = suggest_params(trial, name)
        try:
            predictions = [predict(train(name, params, fit_rows), val_rows) for fit_rows, val_rows in folds]
        except (FloatingPointError, OverflowError, ValueError):
            return float("inf")
        rows = pd.concat([val_rows for _, val_rows in folds])
        return macro_wape(rows, pd.concat(predictions))

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=TRIALS_PER_MODEL)
    return study


def main():
    warnings.filterwarnings("ignore", category=ConvergenceWarning)
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    data = pd.read_parquet(DATASET)
    run = RESULTS / datetime.now().strftime("%Y%m%dT%H%M%S")
    run.mkdir(parents=True)

    trials, best = [], []
    for start in WINDOW_STARTS:
        development = between(data, start, DEVELOPMENT_END)
        for name in MODELS:
            study = tune(name, development)
            params = suggest_params(optuna.trial.FixedTrial(study.best_params), name)
            best.append({
                "window_start": start,
                "model": name,
                "validation_macro_wape": study.best_value,
                "params": params,
            })
            trials += [
                {"window_start": start, "model": name, "trial": trial.number, "macro_wape": trial.value,
                 "state": trial.state.name, "params": json.dumps(trial.params, sort_keys=True)}
                for trial in study.trials
            ]
            print(f"{start} {name}: {study.best_value:.2f}%", flush=True)

    config = {
        "dataset": str(DATASET),
        "dataset_sha256": file_hash(DATASET),
        "seed": SEED,
        "trials_per_model": TRIALS_PER_MODEL,
        "window_starts": WINDOW_STARTS,
        "validation_years": VALIDATION_YEARS,
        "development_end": DEVELOPMENT_END,
        "target": TARGET,
        "features": FEATURES,
        "models": list(MODELS),
        "versions": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "optuna": optuna.__version__,
        },
    }
    (run / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    (run / "best_params.json").write_text(json.dumps(best, indent=2) + "\n")
    pd.DataFrame(trials).to_csv(run / "trials.csv", index=False)
    print(f"Saved to {run}")


if __name__ == "__main__":
    main()
