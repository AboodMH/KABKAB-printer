from flask import Flask, request, jsonify
from escpos.printer import Usb
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
from datetime import datetime

app = Flask(__name__)

# دالة لترتيب النصوص العربية
def ar(text: str) -> str:
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)   # ترتيب الحروف
    bidi_text = get_display(reshaped)          # عكس الاتجاه RTL
    return bidi_text

# إعداد الطابعة (عدل الـ VendorID و ProductID حسب طابعتك)
p = Usb(0x0fe6, 0x811e, interface=0, out_ep=0x02)

@app.route('/print', methods=['POST'])
def print_invoice():
    data = request.json

    # بيانات من ال JSON
    cashier = data.get('cashier', 'غير معروف')
    invoice_number = data.get('invoice_no', '0000')
    date_time = data.get('date_time', datetime.now().strftime("%Y-%m-%d %H:%M"))
    items = data.get('items', [])
    payments = data.get('payments', [])
    note = data.get('note', '')

    # ثوابت ثابتة
    store_name = "KABKAB"
    phone = "0776078047"
    location = "عمان - المدينة الرياضية - مجمع السهلي"

    # إعداد الخطوط
    header_font = ImageFont.truetype("Amiri-Bold.ttf", 90)
    regular_font = ImageFont.truetype("Amiri-Bold.ttf", 32)
    small_font = ImageFont.truetype("Amiri-Bold.ttf", 24)
    table_font = ImageFont.truetype("Amiri-Bold.ttf", 24)
    bold_phone_font = ImageFont.truetype("Amiri-Bold.ttf", 30)

    width = 576
    line_height = 50
    padding = 20
    base_lines = 15
    total_lines = base_lines + len(items) + 2
    height = padding * 2 + total_lines * line_height

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    def draw_rtl(text, y, font=regular_font, align="right"):
        shaped = ar(text)  # ← هنا صار فيه bidi + reshaper
        bbox = draw.textbbox((0, 0), shaped, font=font)
        text_width = bbox[2] - bbox[0]
        if align == "right":
            x = width - padding - text_width
        elif align == "left":
            x = padding
        else:
            x = (width - text_width) // 2
        draw.text((x, y), shaped, font=font, fill="black")

    def draw_column_text(text, col_x, col_w, y, font=table_font, center=False):
        shaped = ar(text)  # ← وهنا كمان
        bbox = draw.textbbox((0, 0), shaped, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_y = y + (line_height - text_height) // 2
        if center:
            text_x = col_x + (col_w - text_width) // 2
        else:
            text_x = col_x + 5
        draw.text((text_x, text_y), shaped, font=font, fill="black")

    # --- باقي الكود تبعك بدون تغيير ---
    # (يظل كما كتبته: رسم رأس الفاتورة، الجدول، الحسابات، الخ...)

    bw = img.convert("L")
    p.image(bw)
    p.cut()

    return jsonify({"status": "success", "message": "تمت الطباعة بنجاح"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9000)
