from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from books.models import Category, Book, Cart

router = Router()


# ==================== DJANGO ORM FUNCTIONS ====================
@sync_to_async
def get_all_categories():
    return list(Category.objects.all())


@sync_to_async
def get_books_by_category(category_id):
    return list(Book.objects.filter(category_id=category_id, is_available=True))


@sync_to_async
def get_book_details(book_id):
    return Book.objects.select_related('category').get(id=book_id)


@sync_to_async
def add_to_db_cart(user_id, book_id):
    # Agar savatda bu kitob bo'lsa, sonini oshiradi, yo'q bo'lsa yangi ochadi
    cart_item, created = Cart.objects.get_or_create(user_id=user_id, book_id=book_id)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return cart_item


@sync_to_async
def get_user_cart(user_id):
    return list(Cart.objects.filter(user_id=user_id).select_related('book'))


@sync_to_async
def clear_user_cart(user_id):
    Cart.objects.filter(user_id=user_id).delete()


# ==================== HANDLERS ====================

# 1. KLAVIATURADAGI "Kitoblar katalogi" TUGMASI
@router.message(F.text.contains("Kitoblar katalogi"))
async def show_categories(message: types.Message):
    categories = await get_all_categories()

    if not categories:
        await message.answer("⚠️ Hozircha do'konimizda birorta ham janr/kategoriya mavjud emas.")
        return

    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat.name, callback_data=f"category_{cat.id}")

    builder.adjust(2)
    await message.answer("📚 Janrlardan birini tanlang:", reply_markup=builder.as_markup())


# 2. INLINE JANR TUGMASI BOSILGANDA (KITOBLAR RO'YXATI - YANGILANDI)
@router.callback_query(F.data.startswith("category_"))
async def show_books(callback: types.CallbackQuery):
    category_id = int(callback.data.split("_")[-1])
    books = await get_books_by_category(category_id)

    if not books:
        await callback.answer("Bu janrda hozircha sotuvda kitoblar yo'q.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for book in books:
        builder.button(text=f"📖 {book.title}", callback_data=f"book_{book.id}")

    builder.button(text="⬅️ Janrlarga qaytish", callback_data="back_to_genres")
    builder.adjust(1)

    text_content = "Kitobni tanlang:"

    # Trash-safe tahrirlash: Agar eski xabarda rasm bo'lsa edit_text xato beradi.
    # Shuning uchun rasm bor-yo'qligini tekshirib, xavfsiz boshqarish kodini yozdik:
    if callback.message.photo:
        # Rasmli xabar bo'lsa, uni o'chirib yangi toza xabar ko'rinishida janr kitoblarini chiqaramiz
        await callback.message.delete()
        await callback.message.answer(text=text_content, reply_markup=builder.as_markup())
    else:
        # Oddiy matnli xabar bo'lsa, o'z joyida silliq tahrirlaymiz
        await callback.message.edit_text(text=text_content, reply_markup=builder.as_markup())

    await callback.answer()


# 3. KITOB TUGMASI BOSILGANDA (KITOB HAQIDA TO'LIQ MA'LUMOT)
@router.callback_query(F.data.startswith("book_"))
async def show_book_info(callback: types.CallbackQuery):
    book_id = int(callback.data.split("_")[1])
    book = await get_book_details(book_id)

    await callback.message.delete()

    price_text = f"{book.price} so'm"
    if book.discount_price:
        price_text = f"<s>{book.price} so'm</s> {book.discount_price} so'm"

    caption = (
        f"📚 <b>{book.title}</b>\n"
        f"✍️ <b>Muallif:</b> {book.author}\n"
        f"🗂 <b>Janr:</b> {book.category.name}\n\n"
        f"📋 <b>Tavsif:</b>\n<i>{book.description}</i>\n\n"
        f"ℹ️ <b>Ma'lumotlar:</b>\n"
        f"• Sahifalar: {book.pages or 'Noma\'lum'}\n"
        f"• Tili: {book.get_language_display()}\n"
        f"• Muqova: {book.get_cover_type_display()}\n"
        f"• Yili: {book.published_year or 'Noma\'lum'}-yil\n\n"
        f"💰 <b>Narxi:</b> {price_text}\n"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🛒 Savatga qo'shish", callback_data=f"add_cart_{book.id}")
    builder.button(text="⬅️ Janrga qaytish", callback_data=f"category_{book.category.id}")
    builder.adjust(1, 1)

    if book.image:
        from aiogram.types import FSInputFile
        try:
            photo = FSInputFile(book.image.path)
            await callback.message.answer_photo(photo=photo, caption=caption, parse_mode="HTML",
                                                reply_markup=builder.as_markup())
        except Exception:
            await callback.message.answer(text=caption, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await callback.message.answer(text=caption, parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()


# 4. JANRLARGA QAYTISH TUGMASI BOSILGANDA
@router.callback_query(F.data == "back_to_genres")
async def back_to_genres_handler(callback: types.CallbackQuery):
    categories = await get_all_categories()

    if not categories:
        await callback.answer("⚠️ Janrlar topilmadi.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.button(text=cat.name, callback_data=f"category_{cat.id}")

    builder.adjust(2)
    await callback.message.edit_text(text="📚 Janrlardan birini tanlang:", reply_markup=builder.as_markup())
    await callback.answer()


# 5. SAVATGA QO'SHISH TUGMASI BOSILGANDA (TOZALANDI VA TO'G'RILANDI)
@router.callback_query(F.data.startswith("add_cart_"))
async def handle_add_to_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    book_id = int(callback.data.split("_")[-1])

    print("=" * 40)
    print(f"DEBUG: Savatga qo'shish jarayoni boshlandi!")
    print(f"User ID: {user_id} | Book ID: {book_id}")

    # Savatni bazaga yozish funksiyasini chaqiramiz
    cart_item = await add_to_db_cart(user_id=user_id, book_id=book_id)

    print(f"DATABASE SUCCESS: Savatdagi umumiy soni: {cart_item.quantity} ta")
    print("=" * 40)

    await callback.answer("🛒 Kitob savatingizga muvaffaqiyatli qo'shildi!", show_alert=True)


# 6. SAVATNI KO'RISH TUGMASI (KLAVIATURADAN)
@router.message(F.text.contains("Savatni ko'rish"))
async def show_cart(message: types.Message):
    user_id = message.from_user.id
    cart_items = await get_user_cart(user_id)

    if not cart_items:
        await message.answer("🛒 Sizning savatingiz bo'sh. Katalog bo'limidan kitoblar qo'shishingiz mumkin.")
        return

    text = "🛒 <b>Sizning savatingiz:</b>\n\n"
    total_price = 0

    for item in cart_items:
        current_price = item.book.discount_price if item.book.discount_price else item.book.price
        item_total = current_price * item.quantity
        total_price += item_total

        text += (
            f"📖 <b>{item.book.title}</b>\n"
            f"└ {item.quantity} ta x {current_price} = {item_total} so'm\n\n"
        )

    text += f"💵 <b>Umumiy summa:</b> {total_price} so'm"

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Buyurtmani rasmiylashtirish", callback_data="checkout_order")
    builder.button(text="🗑 Savatni tozalash", callback_data="clear_cart")
    builder.adjust(1, 1)

    await message.answer(text=text, parse_mode="HTML", reply_markup=builder.as_markup())


# 8. SAVATNI TOZALASH (INLINE TUGMA)
@router.callback_query(F.data == "clear_cart")
async def clear_cart_handler(callback: types.CallbackQuery):
    await clear_user_cart(callback.from_user.id)
    await callback.message.delete()
    await callback.message.answer("🗑 Savatingiz butunlay tozalandi.")
    await callback.answer()
