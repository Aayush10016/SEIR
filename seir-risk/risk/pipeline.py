"""Development pipeline: everything fitted on train and selected on validation, never on test/holdout."""

from dataclasses import dataclass, field

import pandas as pd
from sklearn.dummy import DummyClassifier

from risk.baseline import RuleBasedBaseline
from risk.config import RANDOM_SEED, SELECTION_METRIC
from risk.data import Split, get_split, select_features
from risk.evaluate import classification_metrics
from risk.models import MODEL_FAMILIES, TunedModel, evaluate_on, tune

# Chance-level references: any real model must clear these to mean anything.
REFERENCE_STRATEGIES = {"majority_class": "most_frequent", "stratified_random": "stratified"}


@dataclass
class DevelopmentRun:
    families: tuple[str, ...] | None  # evidence families used (None = all)
    features: list[str]
    train: Split
    validation: Split
    references: dict[str, DummyClassifier] = field(default_factory=dict)
    baseline: RuleBasedBaseline | None = None
    models: dict[str, TunedModel] = field(default_factory=dict)

    @property
    def selected_family(self) -> str:
        """Pre-registered rule: best validation macro-F1 (ties: lower log loss)."""
        return max(self.models, key=lambda f: (self.models[f].validation[SELECTION_METRIC],
                                               -self.models[f].validation["log_loss"]))

    @property
    def selected(self) -> TunedModel:
        return self.models[self.selected_family]


def develop(df: pd.DataFrame, manifest: dict, families: tuple[str, ...] | None = None,
            model_families: tuple[str, ...] = MODEL_FAMILIES, with_baseline: bool = True,
            train_repos: set[str] | None = None) -> DevelopmentRun:
    """`train_repos` restricts training to some projects (validation is always the full split)."""
    features = select_features(manifest, families)
    run = DevelopmentRun(
        families=families,
        features=features,
        train=get_split(df, manifest, "train", features, repos=train_repos),
        validation=get_split(df, manifest, "validation", features),
    )
    for name, strategy in REFERENCE_STRATEGIES.items():
        run.references[name] = DummyClassifier(strategy=strategy, random_state=RANDOM_SEED).fit(
            run.train.X, run.train.y)
    if with_baseline:
        run.baseline = RuleBasedBaseline().fit(run.train.X).fit_thresholds(run.validation.X, run.validation.y)
    for family in model_families:
        run.models[family] = tune(family, run.train, run.validation)
    return run


def all_predictors(run: DevelopmentRun) -> dict[str, object]:
    """Name -> object with .predict(X), in report order: references, baseline, models."""
    predictors: dict[str, object] = dict(run.references)
    if run.baseline is not None:
        predictors["rule_baseline"] = run.baseline
    predictors.update(run.models)
    return predictors


def score_split(run: DevelopmentRun, split: Split) -> dict[str, dict]:
    """Class metrics for every predictor; probability metrics too where scores exist."""
    results = {}
    for name, predictor in all_predictors(run).items():
        if isinstance(predictor, TunedModel):
            results[name] = evaluate_on(predictor.estimator, split)
        else:
            results[name] = classification_metrics(split.y, predictor.predict(split.X))
    return results
