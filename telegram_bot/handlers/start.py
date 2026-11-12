from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder

router=Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.button(text="📚 Kitoblar katalogi")
    builder.button(text="🛒 Savatni ko'rish")  # <-- YANGI TUGMA
    builder.button(text="ℹ️ Biz haqimizda")
    builder.adjust(1, 1, 1)  # Har bir tugma alohida qatorda

    await message.answer(
        f"Assalomu alaykum, {message.from_user.full_name}!\n\n"
        f"Kitoblar do'konimiz botiga xush kelibsiz. Quyidagi tugmalardan birini tanlang:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# telegram_bot/handlers/start.py faylining oxiriga qo'shing:

@router.message(F.text.contains("Biz haqimizda"))
async def cmd_about(message: types.Message):
    about_text = (
        "📚 <b>Book Store Bot</b> — sizning sevimli kitob do'koningiz!\n\n"
        "📍 <b>Manzilimiz:</b> Toshkent shahri, Chilonzor tumani, 9-kvartal.\n"
        "📞 <b>Aloqa uchun:</b> +998 (90) 123-45-67\n"
        "🤖 <b>Ish vaqti:</b> 24/7 (Avtomatlashtirilgan tizim)\n\n"
        "Biz orqali eng sara badiiy, biznes va diniy kitoblarni uyingizdan chiqmasdan turib buyurtma qilishingiz mumkin. Xaridingiz fayzli bo'lsin!"
    )
    await message.answer(text=about_text, parse_mode="HTML")
