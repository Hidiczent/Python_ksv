from unittest import result
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import json
import urllib
app = Flask(__name__, static_url_path='/images', static_folder='static/images')
CORS(app, resources={r"/*": {"origins": "*"}})

# ===== 1. Load association rules (from FP-Growth) =====
with open("rules.json", "r", encoding="utf-8") as f:
    rule_data = json.load(f)
rules = pd.DataFrame(rule_data)

# ===== 2. Load Data  =====
products_df = pd.read_csv("data/Extracted_Product_Categories.csv")

# ✅ เพิ่ม image_url ให้กับ products_df
products_df["image_url"] = products_df["ชื่อสินค้า"].apply(
    lambda name: f"http://127.0.0.1:5000/static/images/{urllib.parse.quote(name)}.jpg"
)
# อ่านข้อมูลยอดขายจาก Excel
sales_df1 = pd.read_excel("data/month1.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "วันที่" , "รหัสสินค้า", "หน่วย"]]
sales_df2 = pd.read_excel("data/month2.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "วันที่" , "รหัสสินค้า", "หน่วย"]]
sales_df3 = pd.read_excel("data/month3.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "วันที่" , "รหัสสินค้า", "หน่วย"]]

# รวมข้อมูลยอดขาย
sales_df = pd.concat([sales_df1, sales_df2, sales_df3], ignore_index=True)
full_sales_df = pd.concat([sales_df1, sales_df2, sales_df3], ignore_index=True)

# ✅ รวมกับ products_df ที่มี image_url แล้ว
sales_df = sales_df.merge(products_df, on="ชื่อสินค้า", how="left")
# กรองหมวดหมู่ที่ไม่รู้จักออก
# 🔥 ลบคำว่า "ຢາສາມັນປະຈຳບ້ານ" ออกจากหมวดหมู่
sales_df["หมวดหมู่"] = sales_df["หมวดหมู่"].str.replace("ຢາສາມັນປະຈຳບ້ານ", "", regex=False).str.strip()

# อัปเดต categories ใหม่
categories = sorted(sales_df["หมวดหมู่"].dropna().unique())

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
        .head(10)
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

    pair_rules = pair_rules.sort_values(by="support", ascending=False).head(10)

    return jsonify(pair_rules[["pair", "support", "confidence", "lift"]].to_dict(orient="records"))

# ===== API 4: all categories =====
@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = sales_df["หมวดหมู่"].dropna().unique().tolist()
    # กรองออก
    exclude = ["-", "ຢາສາມັນປະຈໍາບ້ານ","ຂອງຫວານ"]
    filtered_categories = [c for c in categories if c not in exclude]

    return jsonify({"categories": filtered_categories})

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

import os

@app.route('/api/products', methods=['GET'])
def get_all_products():
    products_df = pd.read_csv("data/Extracted_Product_Categories.csv")
    products_df = products_df.dropna(subset=['ชื่อสินค้า', 'หมวดหมู่'])

    sales_df1 = pd.read_excel("data/month1.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "รหัสสินค้า"]]
    sales_df2 = pd.read_excel("data/month2.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "รหัสสินค้า"]]
    sales_df3 = pd.read_excel("data/month3.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "รหัสสินค้า"]]

    sales_df = pd.concat([sales_df1, sales_df2, sales_df3], ignore_index=True)

    merged_df = sales_df.merge(products_df, on='ชื่อสินค้า', how='left')
    merged_df = merged_df[['รหัสสินค้า', 'ชื่อสินค้า', 'หมวดหมู่']].drop_duplicates()

    merged_df = merged_df.rename(columns={
        'รหัสสินค้า': 'id',
        'ชื่อสินค้า': 'name',
        'หมวดหมู่': 'type'
    })

    # ✅ กรอง NaN และแปลง id เป็น str
    merged_df = merged_df[merged_df['id'].notna()]
    merged_df['id'] = merged_df['id'].astype(str)

    # ✅ สร้าง path รูปจาก id แทน name
    merged_df['image'] = merged_df['id'].apply(
        lambda pid: f"/images/{pid}.jpg" if os.path.exists(f"static/images/{pid}.jpg") else None
    )

    return jsonify(merged_df.to_dict(orient='records'))


import os

@app.route('/api/products/<product_id>', methods=['GET'])
def get_product_detail(product_id):
    if not product_id or product_id.strip().lower() == 'nan':
        return jsonify({'error': 'Invalid product ID'}), 400

    # หายอดขายทั้งหมด
    product_sales = full_sales_df[full_sales_df['รหัสสินค้า'].astype(str) == str(product_id)]

    if product_sales.empty:
        return jsonify({'error': 'Product not found'}), 404

    # ชื่อสินค้า
    product_name = product_sales['ชื่อสินค้า'].iloc[0]
    unit = product_sales['หน่วย'].iloc[0]

    # product info จากชื่อ
    product_info = products_df[products_df['ชื่อสินค้า'] == product_name]

    # ยอดขายรายวัน
    daily_sales = product_sales.groupby('วันที่').size().reset_index(name='times_sold')

    # ✅ ตรวจสอบว่าไฟล์ภาพมีอยู่หรือไม่
    image_filename = f"{product_id}.jpg"
    image_path = os.path.join("static/images", image_filename)
    image_url = f"/images/{image_filename}" if os.path.exists(image_path) else None

    detail = {
        'id': product_id,
        'name': product_name,
        'unit': unit,
        'category': product_info['หมวดหมู่'].iloc[0] if not product_info.empty else None,
        'image': image_url,  # ✅ เปลี่ยนจาก image_url → image
        'total_sold': len(product_sales),
        'first_sold_date': str(product_sales['วันที่'].min()),
        'last_sold_date': str(product_sales['วันที่'].max()),
        'times_sold_per_day': daily_sales.to_dict(orient='records')
    }

    return jsonify(detail)


# @app.route('/api/products/popular', methods=['GET'])
# def get_popular_products():
#     top_products = (
#         sales_df
#         .groupby("ชื่อสินค้า")
#         .size()
#         .sort_values(ascending=False)
#         .head(10)
#         .index.tolist()
#     )
#     return jsonify({"popular": top_products})


@app.route('/api/products/popular', methods=['GET'])
def get_popular_products():
    # Step 1: หา top 10 ชื่อสินค้าขายดี
    top_products = (
        sales_df.groupby("ชื่อสินค้า")
        .size()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    top_products.columns = ['name', 'total_sold']

    # Step 2: โหลด products_df และ sales_df ใหม่
    products_df_local = pd.read_csv("data/Extracted_Product_Categories.csv")
    products_df_local = products_df_local.dropna(subset=['ชื่อสินค้า', 'หมวดหมู่'])

    sales_df1 = pd.read_excel("data/month1.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "รหัสสินค้า"]]
    sales_df2 = pd.read_excel("data/month2.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "รหัสสินค้า"]]
    sales_df3 = pd.read_excel("data/month3.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "รหัสสินค้า"]]
    local_sales_df = pd.concat([sales_df1, sales_df2, sales_df3], ignore_index=True)

    # Step 3: รวมเพื่อให้ได้ id และหมวดหมู่
    merged_df = local_sales_df.merge(products_df_local, on='ชื่อสินค้า', how='left')
    merged_df = merged_df[['รหัสสินค้า', 'ชื่อสินค้า', 'หมวดหมู่']].drop_duplicates()
    merged_df = merged_df.rename(columns={
        'รหัสสินค้า': 'id',
        'ชื่อสินค้า': 'name',
        'หมวดหมู่': 'category'
    })
    merged_df['id'] = merged_df['id'].astype(str)

    # Step 4: join กับ top_products
    result = top_products.merge(merged_df, on='name', how='left')

    # ✅ Step 5: ใส่ path รูปภาพ โดยใช้ชื่อสินค้าโดยตรง
    result['image_url'] = result['id'].apply(
    lambda id: f"/images/{id}.jpg"
    )

    return jsonify({"popular": result.to_dict(orient="records")})


from collections import Counter
from itertools import combinations
from flask import jsonify

from flask import jsonify
import pandas as pd



@app.route('/api/products/pairs/<product_id>', methods=['GET'])
def get_pair_recommendations(product_id):
    # 🔹 โหลดข้อมูล
    df1 = pd.read_excel("data/month1.xlsx", sheet_name="รายงานรายวัน")
    df2 = pd.read_excel("data/month2.xlsx", sheet_name="รายงานรายวัน")
    df3 = pd.read_excel("data/month3.xlsx", sheet_name="รายงานรายวัน")
    sales_df = pd.concat([df1, df2, df3], ignore_index=True)

    # 🔹 โหลดข้อมูล product info
    products_df = pd.read_csv("data/Extracted_Product_Categories.csv")
    products_df = products_df.dropna(subset=['ชื่อสินค้า', 'หมวดหมู่'])

    # 🔹 กรองเฉพาะรายการที่ขายออกเท่านั้น
    sales_df = sales_df[sales_df['ขายออก'] > 0]

    # 🔹 ใส่คอลัมน์ "transaction_id" เพื่อใช้แทน "บิล" (ร้าน+วันที่)
    sales_df['transaction_id'] = sales_df['ร้าน'].astype(str) + "-" + sales_df['วันที่'].astype(str)

    # 🔹 กรองเฉพาะธุรกรรมที่มี product_id นี้
    relevant_tx = sales_df[sales_df['รหัสสินค้า'].astype(str) == product_id]['transaction_id'].unique()

    # 🔹 หา product_id อื่น ๆ ที่อยู่ในบิลเดียวกัน
    co_purchased = sales_df[sales_df['transaction_id'].isin(relevant_tx)]
    co_purchased = co_purchased[co_purchased['รหัสสินค้า'].astype(str) != product_id]

    # 🔹 นับความถี่
    top_pairs = (
        co_purchased.groupby(['รหัสสินค้า', 'ชื่อสินค้า'])
        .size()
        .reset_index(name='count')
        .sort_values(by='count', ascending=False)
        .head(10)
    )

    # 🔹 เพิ่ม category และรูปภาพจาก product CSV
    result = top_pairs.merge(products_df, on='ชื่อสินค้า', how='left')
    result['id'] = result['รหัสสินค้า'].astype(str)
    result['category'] = result['หมวดหมู่']
    result['image_url'] = result['id'].apply(lambda pid: f"/images/{pid}.jpg")

    # 🔹 สร้างผลลัพธ์ JSON
    output = result[['id', 'ชื่อสินค้า', 'category', 'image_url']].rename(
        columns={'ชื่อสินค้า': 'name'}
    )

    return jsonify({"pairs": output.to_dict(orient="records")})




# ===== API 9: Get product by Name =====
@app.route('/api/products/name/<product_name>', methods=['GET'])
def get_product_by_name(product_name):
    full_sales = pd.concat([sales_df1, sales_df2, sales_df3], ignore_index=True)

    # กรองเฉพาะสินค้าที่ต้องการ
    product_data = full_sales[full_sales['ชื่อสินค้า'] == product_name]

    if product_data.empty:
        return jsonify({'error': 'Product not found'}), 404

    # นับยอดขายต่อวัน
    daily_sales = product_data.groupby('วันที่').size().reset_index(name='times_sold')
    daily_sales = daily_sales.sort_values(by='วันที่')

    detail = {
        'name': product_name,
        'total_sold': len(product_data),
        'daily_sales': daily_sales.to_dict(orient='records'),
        'first_sold_date': str(product_data['วันที่'].min()),
        'last_sold_date': str(product_data['วันที่'].max())
    }

    return jsonify(detail)

if __name__ == '__main__':
    app.run(debug=True,port=5050)
