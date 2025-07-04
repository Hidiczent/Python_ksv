from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import json

app = Flask(__name__)
CORS(app)

# ===== 1. โหลด association rules (จาก FP-Growth) =====
with open("rules.json", "r", encoding="utf-8") as f:
    rule_data = json.load(f)
rules = pd.DataFrame(rule_data)

# ===== 2. โหลดข้อมูลสินค้าขายดีต่อหมวดหมู่ =====
products_df = pd.read_csv("data/Extracted_Product_Categories.csv")
sales_df1 = pd.read_excel("data/month1.xlsx", sheet_name="รายงานรายวัน", skiprows=6)[["ชื่อสินค้า", "วันที่"]]
sales_df2 = pd.read_excel("data/month2.xlsx", sheet_name="รายงานรายวัน", skiprows=6)[["ชื่อสินค้า", "วันที่"]]
sales_df3 = pd.read_excel("data/month3.xlsx", sheet_name="รายงานรายวัน", skiprows=6)[["ชื่อสินค้า", "วันที่"]]

sales_df = pd.concat([sales_df1, sales_df2, sales_df3], ignore_index=True)
sales_df = sales_df.merge(products_df, on="ชื่อสินค้า", how="left")
sales_df = sales_df.dropna(subset=["หมวดหมู่"])

categories = sorted(products_df["หมวดหมู่"].dropna().unique())

# ===== API 1: แนะนำสินค้าจาก association rules =====
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

# ===== API 2: แนะนำสินค้าขายดีในหมวดหมู่ =====
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

# ===== API 3: คู่สินค้าที่มักซื้อคู่กันบ่อย =====
@app.route('/api/top-pairs', methods=['GET'])
def top_pairs():
    pair_rules = rules[
        (rules['antecedents'].apply(len) == 1) &
        (rules['consequents'].apply(len) == 1)
    ].copy()

    pair_rules["pair"] = pair_rules.apply(
        lambda row: f"{list(row['antecedents'])[0]} ↔ {list(row['consequents'])[0]}", axis=1
    )

    pair_rules = pair_rules.sort_values(by="support", ascending=False).head(10)

    return jsonify(pair_rules[["pair", "support", "confidence", "lift"]].to_dict(orient="records"))

# ===== API 4: หมวดหมู่ทั้งหมด =====
@app.route('/api/categories', methods=['GET'])
def get_categories():
    return jsonify({"categories": categories})

# ===== API 5: แนะนำสินค้าที่มักซื้อคู่กับสินค้าที่เลือก =====
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

# ===== API 6: rules ทั้งหมด (debug ใช้ดูได้) =====
@app.route('/api/rules', methods=['GET'])
def get_rules():
    return jsonify(rules.to_dict(orient="records"))

if __name__ == '__main__':
    app.run(debug=True)
