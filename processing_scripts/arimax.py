"""This module contains functions to fit ARIMAX models to the data and extract results in a consistent format."""

from pmdarima import auto_arima
from statsmodels.tsa.statespace.sarimax import SARIMAX

def fit_best_arimax(y, X):
    # Use pmdarima to find the best variable rather than doing a manual grid search
    # It pretty much just picks the best values for the AR and MA parts of ARIMA
    auto_model = auto_arima(
        y,
        exogenous=X,
        start_p=0,
        max_p=3,
        start_q=0,
        max_q=3,
        max_d=2,
        seasonal=False,
        stepwise=True,
        suppress_warnings=True,
        error_action="ignore",
        information_criterion="aic",
    )
    order = auto_model.order
 
    # Apply the best order to a SARIMAX model
    # Seasonal component is disabled.
    model = SARIMAX(
        y,
        exog=X,
        order=order,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    result = model.fit(disp=False)
 
    return result, order

def extract_results(repo, results, order):
    params = results.params
    pvalues = results.pvalues
    conf = results.conf_int()

    def safe_get(series, key):
        return float(series[key]) if key in series else None

    return {
        "repo": repo.url,
        "order": str(order),

        "coef_post": safe_get(params, "post"),
        "coef_time_after": safe_get(params, "time_after"),

        "p_post": safe_get(pvalues, "post"),
        "p_time_after": safe_get(pvalues, "time_after"),

        "ci_low_post": safe_get(conf[0], "post"),
        "ci_high_post": safe_get(conf[1], "post"),

        "ci_low_time_after": safe_get(conf[0], "time_after"),
        "ci_high_time_after": safe_get(conf[1], "time_after"),

        "aic": results.aic,
        "bic": results.bic,

        "ar1": safe_get(params, "ar.L1"),
        "ma1": safe_get(params, "ma.L1"),

        "significant_post": safe_get(pvalues, "post") < 0.05 if "post" in pvalues else False, # type: ignore
        "significant_trend": safe_get(pvalues, "time_after") < 0.05 if "time_after" in pvalues else False, # type: ignore
    }