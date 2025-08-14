from flask import Flask, request, jsonify
from escpos.printer import Usb
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from datetime import datetime

app = Flask(__name__)

def ar(text):
    return arabic_reshaper.reshape(text)

# إعداد الطابعة (عدل الباركود حسب طابعتك)
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
        shaped = ar(text)
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
        shaped = ar(text)
        bbox = draw.textbbox((0, 0), shaped, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_y = y + (line_height - text_height) // 2
        if center:
            text_x = col_x + (col_w - text_width) // 2
        else:
            text_x = col_x + 5
        draw.text((text_x, text_y), shaped, font=font, fill="black")

    y = padding - 20
    draw_rtl(store_name, y, font=header_font, align="center")
    y += 110

    draw_rtl(location, y, font=bold_phone_font, align="center")
    y += line_height

    draw_rtl(f"Tel: {phone}", y, font=bold_phone_font, align="center")
    y += int(line_height)  # تقليل المسافة

    draw.line((padding, y, width - padding, y), fill="black", width=2)
    y += 20

    draw_rtl(f"التاريخ والوقت: {date_time}", y, font=small_font)
    y += line_height
    draw_rtl(f"الكاشير: {cashier}", y, font=small_font)
    y += line_height
    draw_rtl(f"رقم الفاتورة: {invoice_number}", y, font=small_font)
    y += line_height

    draw.line((padding, y, width - padding, y), fill="black", width=2)
    y += 10

    headers = ["المنتج", "السعر", "الكمية", "الإجمالي"]
    col_widths = [280, 80, 80, 100]
    x_positions = []
    x = width - padding
    for w in col_widths:
        x_positions.append(x - w)
        x -= w

    row_top = y
    row_bottom = y + line_height
    for i, head in enumerate(headers):
        col_x = x_positions[i]
        col_w = col_widths[i]
        draw.rectangle([(col_x, row_top), (col_x + col_w, row_bottom)], outline="black", width=2)
        draw_column_text(head, col_x, col_w, y, font=table_font, center=True)
    y += line_height

    total_price = 0
    total_qty = 0
    for item in items:
        product = item.get('product', '')
        qty = int(item.get('qty', 0))
        price = float(item.get('price', 0))
        subtotal = qty * price
        total_price += subtotal
        total_qty += qty
        values = [product, f"{price:.2f}", str(qty), f"{subtotal:.2f}"]
        for i, val in enumerate(values):
            col_x = x_positions[i]
            col_w = col_widths[i]
            draw_column_text(val, col_x, col_w, y, font=table_font, center=True)
        y += line_height

    y += 10
    summary_data = [(str(total_qty), "إجمالي الكمية"), (f"{total_price:.2f} دينار", "المجموع النهائي")]
    total_table_width = width - 2 * padding
    cell_small_w = total_table_width // 4
    cell_large_w = total_table_width - cell_small_w

    for label, value in summary_data:
        x = padding
        draw.rectangle([(x, y), (x + cell_large_w, y + line_height)], outline="black", width=2)
        draw_column_text(label, x, cell_large_w, y, font=small_font, center=True)

        x = padding + cell_large_w
        draw.rectangle([(x, y), (x + cell_small_w, y + line_height)], outline="black", width=2)
        draw_column_text(value, x, cell_small_w, y, font=small_font, center=True)

        y += line_height

    draw.line((padding, y, width - padding, y), fill="black", width=2)
    y += 10

    # الدفع
    payment_data = []
    for pay in payments:
        method = pay.get('payment_method', '')
        amount = float(pay.get('amount_paid', 0))
        payment_data.append((f"{amount:.2f} دينار", method))

    if not payment_data:
        payment_data = [(f"{total_price:.2f} دينار", "نقداً")]

    for label, value in payment_data:
        x = padding
        draw.rectangle([(x, y), (x + cell_large_w, y + line_height)], outline="black", width=2)
        draw_column_text(label, x, cell_large_w, y, font=small_font, center=True)

        x = padding + cell_large_w
        draw.rectangle([(x, y), (x + cell_small_w, y + line_height)], outline="black", width=2)
        draw_column_text(value, x, cell_small_w, y, font=small_font, center=True)

        y += line_height

    # حساب الباقي
    total_cash_price = total_price - sum([float(pay.get('amount_paid', 0)) for pay in payments if pay.get('payment_method') != 'cash'])
    total_cash_paid = sum([float(pay.get('amount_paid', 0)) for pay in payments if pay.get('payment_method') == 'cash'])
    remaining = total_cash_paid - total_cash_price

    x = padding
    draw.rectangle([(x, y), (x + cell_large_w, y + line_height)], outline="black", width=2)
    draw_column_text(f"{remaining:.2f} دينار", x, cell_large_w, y, font=small_font, center=True)

    x = padding + cell_large_w
    draw.rectangle([(x, y), (x + cell_small_w, y + line_height)], outline="black", width=2)
    draw_column_text("الباقي", x, cell_small_w, y, font=small_font, center=True)
    y += line_height

    if note:
        y += 10
        draw.line((padding, y, width - padding, y), fill="black", width=2)
        y += line_height
        draw_rtl(note, y, font=small_font, align="center")
        y += line_height

    y += 10
    draw.line((padding, y, width - padding, y), fill="black", width=2)
    y += int(line_height * 0.6)
    draw_rtl("شكراً لتسوقكم معنا!", y, font=small_font, align="center")
    y += int(line_height * 0.6)
    draw_rtl("لا يُسمح بالاسترجاع، التبديل خلال 3 أيام.", y, font=small_font, align="center")

    bw = img.convert("L")
    p.image(bw)
    p.cut()

    return jsonify({"status": "success", "message": "تمت الطباعة بنجاح"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9000)
