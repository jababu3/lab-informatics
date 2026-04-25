from typing import List, Dict
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
from scipy.optimize import curve_fit


def train_qsar(data: List[Dict], model_type: str = "random_forest"):
    df = pd.DataFrame(data)
    features = ["molecular_weight", "logp", "tpsa", "hbd", "hba", "rotatable_bonds"]
    df_clean = df[features + ["activity_value"]].dropna()

    if len(df_clean) < 10:
        raise ValueError("Need ≥10 compounds")

    X = df_clean[features]
    y = df_clean["activity_value"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = (
        RandomForestRegressor(n_estimators=100, random_state=42)
        if model_type == "random_forest"
        else LinearRegression()
    )
    model.fit(X_train, y_train)

    r2_test = r2_score(y_test, model.predict(X_test))
    rmse_test = np.sqrt(mean_squared_error(y_test, model.predict(X_test)))

    importance = pd.DataFrame(
        {
            "feature": features,
            "importance": (
                model.feature_importances_
                if model_type == "random_forest"
                else abs(model.coef_)
            ),
        }
    ).sort_values("importance", ascending=False)

    return {
        "r2_test": float(r2_test),
        "rmse_test": float(rmse_test),
        "n_samples": len(df_clean),
        "feature_importance": importance.to_dict("records"),
    }


def fit_dose_response(conc: List[float], resp: List[float]):
    conc, resp = np.array(conc), np.array(resp)
    mask = ~(np.isnan(conc) | np.isnan(resp))
    conc, resp = conc[mask], resp[mask]

    if len(conc) < 5:
        raise ValueError("Need ≥5 points")

    def logistic(x, bottom, top, ic50, hill):
        return bottom + (top - bottom) / (1 + (x / ic50) ** hill)

    params, _ = curve_fit(
        logistic,
        conc,
        resp,
        p0=[np.min(resp), np.max(resp), np.median(conc), 1.0],
        bounds=(
            [0, np.max(resp) * 0.5, min(conc) / 100, 0.1],
            [np.min(resp) * 2, np.inf, max(conc) * 100, 10],
        ),
        maxfev=10000,
    )

    bottom, top, ic50, hill = params
    conc_fit = np.logspace(np.log10(min(conc) / 10), np.log10(max(conc) * 10), 100)
    resp_fit = logistic(conc_fit, *params)

    r2 = 1 - np.sum((resp - logistic(conc, *params)) ** 2) / np.sum(
        (resp - np.mean(resp)) ** 2
    )

    return {
        "ic50": float(ic50),
        "hill_slope": float(hill),
        "top": float(top),
        "bottom": float(bottom),
        "r_squared": float(r2),
        "fitted_curve": {
            "concentrations": conc_fit.tolist(),
            "responses": resp_fit.tolist(),
        },
    }
