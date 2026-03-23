# uv run -m productivity.lets_try_again

import pandas as pd
from pmdarima import auto_arima
from statsmodels.tsa.statespace.sarimax import SARIMAX

from interact_with_neo4j import (
    get_file_extension_mappings,
    iter_repos,
    load_df,
)

RESULT_FILE = "./productivity/arimax_results.csv"
MIN_WEEKS = 4

file_extensions_map = get_file_extension_mappings()
print(file_extensions_map)

query = """
MATCH (r:Repository {url: $repoUrl})<-[:PART_OF]-(b:Branch)<-[:IN_BRANCH]-(c:Commit)
WHERE c.date IS NOT NULL
WITH r, c,
     datetime(replace(c.date, ' ', 'T')) AS dt
WITH r,
     date.truncate('week', dt) AS week
RETURN r.url AS repo,
       week,
       count(*) AS commits
ORDER BY week
"""


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

        "significant_post": safe_get(pvalues, "post") < 0.05 if "post" in pvalues else False,
        "significant_trend": safe_get(pvalues, "time_after") < 0.05 if "time_after" in pvalues else False,
    }


rows = []

for repo in iter_repos():

    try:
        df = load_df(query, {"repoUrl": repo.url})

        if df.empty:
            continue

        # convert week to datetime and sort
        df["week"] = df["week"].apply(lambda d: pd.Timestamp(d.isoformat()))
        df["week"] = pd.to_datetime(df["week"])

        artifact_dt = pd.to_datetime(repo.artifact_creation_date)
        artifact_week = artifact_dt.to_period("W").start_time

        # Index on week
        df = df[["week", "commits"]].copy()
        df = df.sort_values("week").set_index("week")

        commits = df["commits"].asfreq("W-MON", fill_value=0)
        df = commits.to_frame()

        # group inito before/after artifact creation
        df["week_offset"] = (df.index - artifact_week).days // 7

        post_weeks = df[df["week_offset"] >= 0].shape[0]
        pre_weeks = df[df["week_offset"] < 0].shape[0]

        if post_weeks < MIN_WEEKS or pre_weeks < MIN_WEEKS:
            continue

        # Trim to only have 1.5x more weeks before than after. 
        max_pre_weeks = int(1.5 * post_weeks)

        df = df[
            (df["week_offset"] >= -max_pre_weeks) &
            (df["week_offset"] < post_weeks)
        ]

        # Statistics...
        df["post"] = (df["week_offset"] >= 0).astype(int)
        df["time"] = range(len(df))
        df["time_after"] = df["time"] * df["post"]

        y = df["commits"]
        X = df[["post", "time_after"]]

        result, order = fit_best_arimax(y, X)

        if result is None:
            print(f"All models failed for {repo.url}")
            continue

        print(f"{repo.url} -> best order: {order}, AIC: {result.aic:.2f}")

        row = extract_results(repo, result, order)
        rows.append(row)

    except Exception as e:
        print(f"Failed for {repo.url}: {e}")


results_df = pd.DataFrame(rows)
print(results_df)

results_df.to_csv(RESULT_FILE, index=False)

n = len(results_df)

post_sig = results_df["p_post"] < 0.05
trend_sig = results_df["p_time_after"] < 0.05

both = (post_sig & trend_sig).mean()
post_only = (post_sig & ~trend_sig).mean()
trend_only = (~post_sig & trend_sig).mean()

print("\nSummary of results:")
print("post significant:", post_sig.mean())
print("trend significant:", trend_sig.mean())
print("both:", both)
print("post only:", post_only)
print("trend only:", trend_only)