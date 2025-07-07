from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import json

app = Flask(__name__)
CORS(app)

# ===== 1. Load association rules (from FP-Growth) =====
with open("rules.json", "r", encoding="utf-8") as f:
    rule_data = json.load(f)
rules = pd.DataFrame(rule_data)

# ===== 2. Load Data  =====
products_df = pd.read_csv("data/Extracted_Product_Categories.csv")
sales_df1 = pd.read_excel("data/month1.xlsx", sheet_name="รายงานรายวัน", skiprows=6)[["ชื่อสินค้า", "วันที่"]]
sales_df2 = pd.read_excel("data/month2.xlsx", sheet_name="รายงานรายวัน", skiprows=6)[["ชื่อสินค้า", "วันที่"]]
sales_df3 = pd.read_excel("data/month3.xlsx", sheet_name="รายงานรายวัน", skiprows=6)[["ชื่อสินค้า", "วันที่"]]

sales_df = pd.concat([sales_df1, sales_df2, sales_df3], ignore_index=True)
sales_df = sales_df.merge(products_df, on="ชื่อสินค้า", how="left")
sales_df = sales_df.dropna(subset=["หมวดหมู่"])

categories = sorted(products_df["หมวดหมู่"].dropna().unique())

# ===== API 1: Recommend product from association rules =====
@app.route('/api/recommend', methods=['POST'])
def recommend():
    input_items = request.json.get('items', [])
    if not input_items:
        return jsonify({'recommendations': []})

    recommendations = set()
    for _, rule in rules.iterrows():
        if set(rule['antecedents']).issubset(input_items):
            recommendations.update(rule['consequents'])

    recommendations -= set(input_items)
    return jsonify({'recommendations': list(recommendations)})

# ===== API 2: Recommend best-selling products in categories =====
@app.route('/api/recommend-products', methods=['POST'])
def recommend_by_category():
    category = request.json.get("category", None)
    if not category:
        return jsonify({"products": []})

    top_products = (
        sales_df[sales_df["หมวดหมู่"] == category]
        .groupby("ชื่อสินค้า")
        .size()
        .sort_values(ascending=False)
        .head(20)
        .index.tolist()
    )

    return jsonify({"products": top_products})

# ===== API 3: Product pairs that are often bought together =====
@app.route('/api/top-pairs', methods=['GET'])
def top_pairs():
    pair_rules = rules[
        (rules['antecedents'].apply(len) == 1) &
        (rules['consequents'].apply(len) == 1)
    ].copy()

    pair_rules["pair"] = pair_rules.apply(
        lambda row: f"{list(row['antecedents'])[0]} ↔ {list(row['consequents'])[0]}", axis=1
    )

    pair_rules = pair_rules.sort_values(by="support", ascending=False).head(20)

    return jsonify(pair_rules[["pair", "support", "confidence", "lift"]].to_dict(orient="records"))

# ===== API 4: all categories =====
@app.route('/api/categories', methods=['GET'])
def get_categories():
    return jsonify({"categories": categories})

# ===== API 5: Recommend products frequently bought together =====
@app.route('/api/pair-recommend', methods=['POST'])
def pair_recommend():
    input_items = set(request.json.get('items', []))
    pair_recommendations = set()

    for _, rule in rules.iterrows():
        antecedent = set(rule["antecedents"])
        consequent = set(rule["consequents"])
        if input_items & antecedent:
            pair_recommendations |= consequent

    pair_recommendations -= input_items
    return jsonify({'pair_recommendations': list(pair_recommendations)})

# ===== API 6: rules all (debug use view only) =====
@app.route('/api/rules', methods=['GET'])
def get_rules():
    def convert_set(value):
        if isinstance(value, frozenset):
            return list(value)
        return value

    cleaned_rules = []
    for _, row in rules.iterrows():
        cleaned_rules.append({
            "antecedents": convert_set(row["antecedents"]),
            "consequents": convert_set(row["consequents"]),
            "support": row["support"],
            "confidence": row["confidence"],
            "lift": row["lift"],
        })

    return jsonify(cleaned_rules)

if __name__ == '__main__':
    app.run(debug=True)
