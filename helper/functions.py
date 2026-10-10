import pandas as pd
import re
from sklearn.linear_model import LinearRegression


def design_matrix(df):
    patterns = {
        "Price": r"Price\s*-?\s*(\$?\s*500\s*-\s*800|\$?\s*800\s*-\s*1000|\$?\s*1000\s*-\s*1500)",
        "RAM": r"RAM\s*-?\s*(8GB\s+or\s+less|above\s+8GB|more\s+than\s+8GB)",
        "Processor": r"Processor\s*-?\s*(Intel\s+i[357])",
        "Weight": r"Weigh(?:t|s)?\s*-?\s*(less\s+than\s+3\s*lbs|3\s*-\s*7\s*lbs|more\s+than\s+7\s*lbs)",
        "OS": r"Operating\s+System\s*-?\s*(Windows|MacOS)"
    }

    rows = []
    for question_id, question_text in df.columns:
        if question_id.startswith("Q5_"):
            row = {"Profile": question_id}
            row.update({
                attr: (m.group(1) if (m := re.search(pattern, question_text, re.I)) else None)
                for attr, pattern in patterns.items()
            })
            rows.append(row)

    result = pd.DataFrame(rows)

    replacements = {
        "RAM": {"8gb or less": "<= 8GB", "above 8gb": "> 8GB", "more than 8gb": "> 8GB"},
        "Weight": {"less than 3 lbs": "< 3 lbs", "3-7lbs": "3–7 lbs", "more than 7lbs": "> 7 lbs","more than 7 lbs": "> 7 lbs", "3–7 lbs": "3–7 lbs", "3 - 7 lbs": "3–7 lbs"},
        "Price":{"$500- 800": "$500–800", "$500 -800": "$500–800","$500-800":"$500–800", "$1000 -1500": "$1000–1500", "$1000-1500":"$1000–1500"}
    }

    for col, mapping in replacements.items():
        normalized = result[col].str.lower().str.replace(r"\s+", "", regex=True)
        result[col] = normalized.replace({key.replace(" ", ""): value for key, value in mapping.items()})

    return result

def calculate_utilities(df):
    attributes = ["Price", "RAM", "Processor", "Weight", "OS"]
    target= "Preference"
    df[target] = 11 - df["Rank"]

    data = df.dropna(subset=attributes + [target]).copy()

    # Create design matrix and fit regression
    X = pd.get_dummies(data[attributes], drop_first=True, dtype=float)
    y = data[target]

    model = LinearRegression()
    model.fit(X, y)

    utilities = []

    for attribute in attributes:
        levels = data[attribute].drop_duplicates().tolist()
        attribute_utilities = []

        for level in levels:
            column = f"{attribute}_{level}"

            utility = (
                model.coef_[X.columns.get_loc(column)]
                if column in X.columns
                else 0.0
            )

            attribute_utilities.append(utility)

        # Center utilities within this attribute
        mean_utility = sum(attribute_utilities) / len(attribute_utilities)

        for level, utility in zip(levels, attribute_utilities):
            utilities.append({
                "Attribute": attribute,
                "Level": level,
                "Utility": utility - mean_utility
            })

    return pd.DataFrame(utilities)


def calculate_importance(utility_df):
    importance_df = (
        utility_df.groupby("Attribute")["Utility"]
        .agg(Min="min", Max="max")
        .assign(Range=lambda x: x["Max"] - x["Min"])
    )

    importance_df["Importance (%)"] = (
        importance_df["Range"] / importance_df["Range"].sum() * 100
    )

    return importance_df.sort_values(
        "Importance (%)", ascending=False
    ).reset_index()

