from flask import Flask, request, jsonify
import win32print
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

app = Flask(__name__)

# إعدادات الملصق
mm_to_dots = 8
label_width_mm = 35
label_height_mm = 23
img_width = label_width_mm * mm_to_dots
img_height = 100

def reshape_arabic(text):
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text

def print_label(store_name, price, product_name, barcode_number):
    image = Image.new("L", (img_width, img_height), 255)
    draw = ImageDraw.Draw(image)

    try:
        font_path = "arial.ttf"
        font_big = ImageFont.truetype(font_path, 24)
        font_normal = ImageFont.truetype(font_path, 20)
    except:
        font_big = font_normal = ImageFont.load_default()

    # رسم اسم المتجر في الأعلى
    y = 5
    store_w = draw.textlength(store_name, font=font_big)
    draw.text(((img_width - store_w) // 2, y), store_name, font=font_big, fill=0)

    # السعر واسم المنتج في سطر واحد
    y += 30
    price_text = reshape_arabic(price)
    product_text = reshape_arabic(product_name)
    price_w = draw.textlength(price_text, font=font_normal)
    product_w = draw.textlength(product_text, font=font_normal)
    total_w = price_w + product_w + 20
    start_x = (img_width - total_w) // 2
    draw.text((start_x, y), price_text, font=font_normal, fill=0)
    draw.text((start_x + price_w + 20, y), product_text, font=font_normal, fill=0)

    # تحويل الصورة إلى أبيض وأسود
    image_bw = image.convert("1")
    bitmap_data = image_bw.tobytes("raw", "1")
    bitmap_width_bytes = img_width // 8
    bitmap_height = img_height

    # إعداد الباركود وموقع الرقم تحته
    barcode_width = 240
    barcode_height = 50
    barcode_x = (img_width - barcode_width) // 2
    barcode_y = img_height - 15

    # حساب تموضع الرقم أسفل الباركود
    char_width = 12  # تقدير تقريبي لحجم كل رقم
    barcode_text_width = len(barcode_number) * char_width
    barcode_text_x = barcode_x + (barcode_width - barcode_text_width) // 2
    barcode_text_y = barcode_y + barcode_height + 5

    # أوامر TSC
    commands = f"""
SIZE {label_width_mm} mm, {label_height_mm} mm
GAP 2 mm, 0
DIRECTION 1
CLS
BITMAP 0,0,{bitmap_width_bytes},{bitmap_height},0,
""".encode("utf-8") + bitmap_data + f"""
BARCODE {barcode_x},{barcode_y},"128",{barcode_height},1,0,2,2,"{barcode_number}"
TEXT {barcode_text_x},{barcode_text_y},"0",0,1,1,"{barcode_number}"
PRINT 1
""".encode("utf-8")

    # الطباعة
    printer_name = "TSC DA200"
    hPrinter = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(hPrinter, 1, ("Label Print", None, "RAW"))
        win32print.StartPagePrinter(hPrinter)
        win32print.WritePrinter(hPrinter, commands)
        win32print.EndPagePrinter(hPrinter)
        win32print.EndDocPrinter(hPrinter)
    finally:
        win32print.ClosePrinter(hPrinter)

@app.route("/print-label", methods=["POST"])
def handle_request():
    data = request.json
    required_fields = ["price", "product_name", "barcode", "quantity"]

    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400

    store_name = "KABKAB"
    price = data["price"]
    product_name = data["product_name"]
    barcode = data["barcode"]
    quantity = int(data["quantity"])

    for i in range(quantity):
        print_label(store_name, price, product_name, barcode)

    return jsonify({"success": True, "message": f"{quantity} labels printed successfully."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
