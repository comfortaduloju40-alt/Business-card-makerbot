import os
import io
import logging
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import telebot
from telebot import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
bot = telebot.TeleBot(BOT_TOKEN)

user_sessions = {}

# ---- Card dimensions (standard business card 3.5 x 2 inch at 300dpi) ----
CARD_W = 1050
CARD_H = 600

THEMES = {
    "Executive Black": {
        "bg_colors":      [(10, 10, 10), (30, 30, 30)],
        "accent":         (212, 175, 55),
        "name_color":     (255, 255, 255),
        "title_color":    (212, 175, 55),
        "body_color":     (200, 200, 200),
        "divider_color":  (212, 175, 55),
        "style":          "diagonal",
    },
    "Clean White": {
        "bg_colors":      [(255, 255, 255), (240, 242, 245)],
        "accent":         (30, 80, 180),
        "name_color":     (15, 25, 50),
        "title_color":    (30, 80, 180),
        "body_color":     (80, 90, 110),
        "divider_color":  (30, 80, 180),
        "style":          "minimal",
    },
    "Navy Pro": {
        "bg_colors":      [(10, 25, 70), (20, 45, 110)],
        "accent":         (100, 200, 255),
        "name_color":     (255, 255, 255),
        "title_color":    (100, 200, 255),
        "body_color":     (180, 210, 240),
        "divider_color":  (100, 200, 255),
        "style":          "corner_bar",
    },
    "Rose Gold": {
        "bg_colors":      [(255, 245, 245), (245, 230, 230)],
        "accent":         (183, 110, 100),
        "name_color":     (80, 30, 25),
        "title_color":    (183, 110, 100),
        "body_color":     (120, 70, 65),
        "divider_color":  (183, 110, 100),
        "style":          "side_bar",
    },
    "Forest Green": {
        "bg_colors":      [(15, 50, 30), (25, 75, 45)],
        "accent":         (120, 210, 140),
        "name_color":     (255, 255, 255),
        "title_color":    (120, 210, 140),
        "body_color":     (180, 230, 195),
        "divider_color":  (120, 210, 140),
        "style":          "corner_bar",
    },
    "Slate Modern": {
        "bg_colors":      [(45, 55, 72), (62, 75, 95)],
        "accent":         (129, 230, 217),
        "name_color":     (255, 255, 255),
        "title_color":    (129, 230, 217),
        "body_color":     (190, 205, 220),
        "divider_color":  (129, 230, 217),
        "style":          "diagonal",
    },
    "Crimson Bold": {
        "bg_colors":      [(140, 10, 20), (100, 5, 15)],
        "accent":         (255, 210, 100),
        "name_color":     (255, 255, 255),
        "title_color":    (255, 210, 100),
        "body_color":     (255, 200, 200),
        "divider_color":  (255, 210, 100),
        "style":          "side_bar",
    },
    "Purple Tech": {
        "bg_colors":      [(30, 10, 60), (55, 20, 100)],
        "accent":         (200, 150, 255),
        "name_color":     (255, 255, 255),
        "title_color":    (200, 150, 255),
        "body_color":     (210, 190, 240),
        "divider_color":  (200, 150, 255),
        "style":          "minimal",
    },
}

STEPS = [
    "theme", "name", "title", "company",
    "email", "phone", "website", "address", "tagline", "logo",
]


# ---- Font helpers ----
def load_font(size, bold=False):
    bold_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    reg_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in (bold_paths if bold else reg_paths):
        try:
            return ImageFont.truetype(p, size)
        except:
            continue
    return ImageFont.load_default()


# ---- Background styles ----
def make_bg(theme):
    c1, c2 = theme["bg_colors"]
    img = Image.new("RGB", (CARD_W, CARD_H))
    draw = ImageDraw.Draw(img)
    for x in range(CARD_W):
        t = x / CARD_W
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(x, 0), (x, CARD_H)], fill=(r, g, b))

    canvas = img.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    style = theme["style"]
    accent = theme["accent"]

    if style == "diagonal":
        # Diagonal accent band bottom-right
        points = [
            (CARD_W * 0.55, CARD_H),
            (CARD_W, CARD_H * 0.3),
            (CARD_W, CARD_H),
        ]
        draw.polygon(points, fill=accent + (18,))
        points2 = [
            (CARD_W * 0.68, CARD_H),
            (CARD_W, CARD_H * 0.55),
            (CARD_W, CARD_H),
        ]
        draw.polygon(points2, fill=accent + (12,))

    elif style == "corner_bar":
        # Top accent bar
        draw.rectangle([(0, 0), (CARD_W, 8)], fill=accent + (255,))
        # Bottom accent bar
        draw.rectangle([(0, CARD_H - 8), (CARD_W, CARD_H)], fill=accent + (255,))

    elif style == "side_bar":
        # Left accent bar
        draw.rectangle([(0, 0), (10, CARD_H)], fill=accent + (255,))
        # Subtle right triangle
        draw.polygon(
            [(CARD_W - 180, CARD_H), (CARD_W, CARD_H - 180), (CARD_W, CARD_H)],
            fill=accent + (30,),
        )

    elif style == "minimal":
        # Just a thin bottom line
        draw.rectangle([(40, CARD_H - 6), (CARD_W - 40, CARD_H - 6)], fill=accent + (200,))

    return canvas


# ---- Logo circle paste ----
def paste_logo(canvas, logo_bytes, x, y, size):
    logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    logo = logo.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([(0, 0), (size - 1, size - 1)], fill=255)
    logo.putalpha(mask)
    canvas.alpha_composite(logo, dest=(x, y))
    # Ring
    draw = ImageDraw.Draw(canvas)
    draw.ellipse([(x - 3, y - 3), (x + size + 3, y + size + 3)],
                 outline=(255, 255, 255, 80), width=2)


# ---- Text helpers ----
def draw_text(draw, x, y, text, font, color, max_width=None):
    if max_width:
        while True:
            bbox = draw.textbbox((0, 0), text, font=font)
            if bbox[2] - bbox[0] <= max_width or len(text) < 5:
                break
            text = text[:-2] + "…"
    draw.text((x, y), text, font=font, fill=color)
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]


def draw_icon_row(draw, x, y, icon, text, font, color, max_width=600):
    full = f"{icon}  {text}"
    draw_text(draw, x, y, full, font, color, max_width=max_width)
    bbox = draw.textbbox((0, 0), full, font=font)
    return bbox[3] - bbox[1]


# ---- Main card renderer ----
def make_card(data: dict) -> bytes:
    theme = THEMES[data["theme"]]
    canvas = make_bg(theme)
    draw = ImageDraw.Draw(canvas)

    has_logo = bool(data.get("logo_bytes"))
    style = theme["style"]

    # Logo
    logo_size = 110
    logo_x = CARD_W - logo_size - 50
    logo_y = 40
    if has_logo:
        paste_logo(canvas, data["logo_bytes"], logo_x, logo_y, logo_size)
        draw = ImageDraw.Draw(canvas)

    # Left content start
    left_pad = 50 if style != "side_bar" else 70
    right_limit = (logo_x - 20) if has_logo else (CARD_W - 60)
    max_text_w = right_limit - left_pad

    y = 55

    # Name
    name = data.get("name", "Your Name")
    name_font = load_font(58, bold=True)
    h = draw_text(draw, left_pad, y, name, name_font, theme["name_color"], max_width=max_text_w)
    y += h + 10

    # Title
    title = data.get("title", "")
    if title:
        title_font = load_font(30)
        h = draw_text(draw, left_pad, y, title, title_font, theme["title_color"], max_width=max_text_w)
        y += h + 6

    # Company
    company = data.get("company", "")
    if company:
        co_font = load_font(26, bold=True)
        h = draw_text(draw, left_pad, y, company, co_font, theme["body_color"], max_width=max_text_w)
        y += h + 4

    # Divider
    y += 14
    div_color = theme["divider_color"] + (180,)
    draw.line([(left_pad, y), (left_pad + 280, y)], fill=div_color, width=2)
    y += 18

    # Contact details
    contact_font = load_font(24)
    line_gap = 34

    email = data.get("email", "")
    if email:
        draw_icon_row(draw, left_pad, y, "✉", email, contact_font, theme["body_color"], max_text_w)
        y += line_gap

    phone = data.get("phone", "")
    if phone:
        draw_icon_row(draw, left_pad, y, "☎", phone, contact_font, theme["body_color"], max_text_w)
        y += line_gap

    website = data.get("website", "")
    if website:
        draw_icon_row(draw, left_pad, y, "🌐", website, contact_font, theme["body_color"], max_text_w)
        y += line_gap

    address = data.get("address", "")
    if address:
        draw_icon_row(draw, left_pad, y, "📍", address, contact_font, theme["body_color"], max_text_w)
        y += line_gap

    # Tagline — bottom of card
    tagline = data.get("tagline", "")
    if tagline:
        tag_font = load_font(22)
        tag_color = theme["accent"] + (200,)
        draw.text((left_pad, CARD_H - 55), f'"{tagline}"', font=tag_font, fill=tag_color)

    # Save
    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True, dpi=(300, 300))
    out.seek(0)
    return out.read()


# ---- Back of card renderer ----
def make_card_back(data: dict) -> bytes:
    theme = THEMES[data["theme"]]
    canvas = make_bg(theme)
    draw = ImageDraw.Draw(canvas)

    # Large centered name initial or logo
    has_logo = bool(data.get("logo_bytes"))
    if has_logo:
        logo_size = 180
        lx = CARD_W // 2 - logo_size // 2
        ly = CARD_H // 2 - logo_size // 2
        paste_logo(canvas, data["logo_bytes"], lx, ly, logo_size)
        draw = ImageDraw.Draw(canvas)
    else:
        # Big initial letter
        initial = (data.get("name") or "?")[0].upper()
        font = load_font(200, bold=True)
        bbox = draw.textbbox((0, 0), initial, font=font)
        iw = bbox[2] - bbox[0]
        ih = bbox[3] - bbox[1]
        ix = (CARD_W - iw) // 2
        iy = (CARD_H - ih) // 2 - 20
        # Shadow
        draw.text((ix + 4, iy + 4), initial, font=font, fill=(0, 0, 0, 60))
        draw.text((ix, iy), initial, font=font, fill=theme["accent"] + (200,))

    # Company bottom
    company = data.get("company", "")
    if company:
        co_font = load_font(28, bold=True)
        bbox = draw.textbbox((0, 0), company, font=co_font)
        cw = bbox[2] - bbox[0]
        cx = (CARD_W - cw) // 2
        draw.text((cx, CARD_H - 65), company, font=co_font, fill=theme["body_color"])

    out = io.BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True, dpi=(300, 300))
    out.seek(0)
    return out.read()


# ---- Bot flow ----

def send_theme_picker(cid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(name, callback_data=f"theme:{name}")
        for name in THEMES
    ]
    markup.add(*buttons)
    bot.send_message(
        cid,
        "🎨 *Step 1 — Choose a theme:*",
        parse_mode="Markdown",
        reply_markup=markup,
    )


@bot.message_handler(commands=["start", "help"])
def cmd_start(message):
    cid = message.chat.id
    bot.send_message(
        cid,
        "👋 *Business Card Maker*\n\n"
        "Create a professional business card in seconds!\n\n"
        "🎨 8 premium themes\n"
        "📇 Front + back of card\n"
        "🖼 Optional logo\n"
        "📐 Print-ready 300 DPI PNG\n\n"
        "Send /make to get started!",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["make"])
def cmd_make(message):
    cid = message.chat.id
    user_sessions[cid] = {"step": "theme"}
    send_theme_picker(cid)


@bot.callback_query_handler(func=lambda call: call.data.startswith("theme:"))
def handle_theme(call):
    cid = call.message.chat.id
    theme = call.data.split(":", 1)[1]
    session = user_sessions.setdefault(cid, {})
    session["theme"] = theme
    session["step"] = "name"
    bot.answer_callback_query(call.id, f"{theme} selected!")
    bot.edit_message_text(
        f"✅ Theme: *{theme}*",
        cid, call.message.message_id, parse_mode="Markdown",
    )
    bot.send_message(
        cid,
        "✏️ *Step 2 — Your full name:*\n_(e.g. Alexandra Johnson)_",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "name")
def handle_name(message):
    cid = message.chat.id
    session = user_sessions[cid]
    session["name"] = message.text.strip()
    session["step"] = "title"
    bot.send_message(
        cid,
        "💼 *Step 3 — Job title:*\n_(e.g. Senior Product Designer)_\nSend /skip to leave blank.",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "title")
def handle_title(message):
    cid = message.chat.id
    session = user_sessions[cid]
    session["title"] = "" if message.text.strip() == "/skip" else message.text.strip()
    session["step"] = "company"
    bot.send_message(
        cid,
        "🏢 *Step 4 — Company name:*\n_(e.g. Acme Corp)_\nSend /skip to leave blank.",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "company")
def handle_company(message):
    cid = message.chat.id
    session = user_sessions[cid]
    session["company"] = "" if message.text.strip() == "/skip" else message.text.strip()
    session["step"] = "email"
    bot.send_message(
        cid,
        "✉️ *Step 5 — Email address:*\n_(e.g. alex@acmecorp.com)_\nSend /skip to leave blank.",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "email")
def handle_email(message):
    cid = message.chat.id
    session = user_sessions[cid]
    session["email"] = "" if message.text.strip() == "/skip" else message.text.strip()
    session["step"] = "phone"
    bot.send_message(
        cid,
        "📞 *Step 6 — Phone number:*\n_(e.g. +1 555 000 1234)_\nSend /skip to leave blank.",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "phone")
def handle_phone(message):
    cid = message.chat.id
    session = user_sessions[cid]
    session["phone"] = "" if message.text.strip() == "/skip" else message.text.strip()
    session["step"] = "website"
    bot.send_message(
        cid,
        "🌐 *Step 7 — Website:*\n_(e.g. www.acmecorp.com)_\nSend /skip to leave blank.",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "website")
def handle_website(message):
    cid = message.chat.id
    session = user_sessions[cid]
    session["website"] = "" if message.text.strip() == "/skip" else message.text.strip()
    session["step"] = "address"
    bot.send_message(
        cid,
        "📍 *Step 8 — Address:*\n_(e.g. 123 Main St, New York, NY)_\nSend /skip to leave blank.",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "address")
def handle_address(message):
    cid = message.chat.id
    session = user_sessions[cid]
    session["address"] = "" if message.text.strip() == "/skip" else message.text.strip()
    session["step"] = "tagline"
    bot.send_message(
        cid,
        "💬 *Step 9 — Tagline:*\n_(e.g. Designing the future, one pixel at a time)_\nSend /skip to leave blank.",
        parse_mode="Markdown",
    )


@bot.message_handler(func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "tagline")
def handle_tagline(message):
    cid = message.chat.id
    session = user_sessions[cid]
    session["tagline"] = "" if message.text.strip() == "/skip" else message.text.strip()
    session["step"] = "logo"
    bot.send_message(
        cid,
        "🖼 *Step 10 — Company logo:*\n_(send as a photo or file — works best with square images)_\nSend /skip to use initials instead.",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["skip"])
def handle_skip(message):
    cid = message.chat.id
    session = user_sessions.get(cid, {})
    if session.get("step") == "logo":
        session["logo_bytes"] = None
        generate_cards(cid)


@bot.message_handler(
    content_types=["photo", "document"],
    func=lambda m: user_sessions.get(m.chat.id, {}).get("step") == "logo",
)
def handle_logo(message):
    cid = message.chat.id
    session = user_sessions.get(cid, {})
    try:
        if message.content_type == "photo":
            file_id = message.photo[-1].file_id
        else:
            if not message.document.mime_type.startswith("image/"):
                bot.send_message(cid, "⚠️ Please send an image.")
                return
            file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        session["logo_bytes"] = bot.download_file(file_info.file_path)
        generate_cards(cid)
    except Exception as e:
        logger.exception("Logo error")
        bot.send_message(cid, f"❌ Error: {e}")


def generate_cards(cid):
    session = user_sessions.get(cid, {})
    msg = bot.send_message(cid, "⏳ Designing your business cards…")
    try:
        front = make_card(session)
        back = make_card_back(session)

        bot.send_photo(
            cid, front,
            caption="📇 *Front of card*",
            parse_mode="Markdown",
        )
        bot.send_photo(
            cid, back,
            caption=(
                "📇 *Back of card*\n\n"
                "✅ Your business cards are ready!\n"
                "Both images are print-ready at 300 DPI.\n\n"
                "Send /make to create another!"
            ),
            parse_mode="Markdown",
        )
        bot.delete_message(cid, msg.message_id)
    except Exception as e:
        logger.exception("Card generation error")
        bot.send_message(cid, f"❌ Failed to generate: {e}")


@bot.message_handler(commands=["cancel"])
def cmd_cancel(message):
    cid = message.chat.id
    user_sessions.pop(cid, None)
    bot.send_message(cid, "❌ Cancelled. Send /make to start over.")


if __name__ == "__main__":
    logger.info("Business card bot starting…")
    bot.infinity_polling()
