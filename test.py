import os
import pandas as pd
import shutil

# 🔹 โหลดข้อมูลสินค้า
products_df = pd.read_csv("data/Extracted_Product_Categories.csv").dropna(subset=['ชื่อสินค้า', 'หมวดหมู่'])

# 🔹 โหลดยอดขายจาก 3 เดือน เพื่อให้ได้ mapping ชื่อสินค้า -> รหัสสินค้า
sales_df1 = pd.read_excel("data/month1.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "รหัสสินค้า"]]
sales_df2 = pd.read_excel("data/month2.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "รหัสสินค้า"]]
sales_df3 = pd.read_excel("data/month3.xlsx", sheet_name="รายงานรายวัน")[["ชื่อสินค้า", "รหัสสินค้า"]]

# 🔹 รวมยอดขายและเอาชื่อสินค้ากับรหัสสินค้าแบบไม่ซ้ำ
sales_df = pd.concat([sales_df1, sales_df2, sales_df3], ignore_index=True).dropna()
sales_df = sales_df.drop_duplicates(subset=["ชื่อสินค้า", "รหัสสินค้า"])

# 🔹 รวมข้อมูลกับ products_df เพื่อความชัวร์
merged_df = sales_df.merge(products_df, on="ชื่อสินค้า", how="left")

# 🔹 สร้าง mapping ชื่อสินค้า ➜ รหัสสินค้า
name_to_id = dict(zip(merged_df["ชื่อสินค้า"], merged_df["รหัสสินค้า"]))

# 🔹 เส้นทางโฟลเดอร์
image_dir = "static/images"

# 🔹 ตรวจสอบและ rename
renamed_count = 0
for filename in os.listdir(image_dir):
    name, ext = os.path.splitext(filename)
    if name in name_to_id:
        product_id = str(name_to_id[name]).strip()
        new_filename = f"{product_id}{ext}"
        old_path = os.path.join(image_dir, filename)
        new_path = os.path.join(image_dir, new_filename)

        # หากชื่อใหม่ยังไม่มีไฟล์นี้
        if not os.path.exists(new_path):
            shutil.move(old_path, new_path)
            print(f"✅ Renamed: {filename} ➜ {new_filename}")
            renamed_count += 1

print(f"\n🔁 Done! Total renamed: {renamed_count}")
