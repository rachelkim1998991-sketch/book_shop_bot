from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from books.models import Cart, Order, OrderItem

router = Router()


# 1. FSM Xolatlari (Bosqichlar)
class OrderSteps(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()


# Django ORM: Asinxron yordamchi funksiyalar
@sync_to_async
def get_user_cart_items(user_id):
    return list(Cart.objects.filter(user_id=user_id).select_related('book'))


@sync_to_async
def create_order_in_db(user_id, full_name, phone_number, address, cart_items):
    total_price = 0
    for item in cart_items:
        price = item.book.discount_price if item.book.discount_price else item.book.price
        total_price += price * item.quantity

    # 1. Asosiy buyurtmani yaratamiz
    order = Order.objects.create(
        user_id=user_id,
        full_name=full_name,
        phone_number=phone_number,
        address=address,
        total_price=total_price,
        status='new'
    )

    # 2. Buyurtma ichidagi kitoblarni bittalab yozamiz
    for item in cart_items:
        price = item.book.discount_price if item.book.discount_price else item.book.price
        OrderItem.objects.create(
            order=order,
            book=item.book,
            quantity=item.quantity,
            price=price
        )

        # Ombordagi sonini kamaytirish (ixtiyoriy, agar stock ishlatilsa)
        if item.book.stock >= item.quantity:
            item.book.stock -= item.quantity
            item.book.save()

    # 3. Savatni tozalaymiz
    Cart.objects.filter(user_id=user_id).delete()
    return order


# ==================== HANDLERS ====================

# 1. "Buyurtmani rasmiylashtirish" INLINE TUGMASI BOSILGANDA
@router.callback_query(F.data == "checkout_order")
async def start_checkout(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    cart_items = await get_user_cart_items(user_id)

    if not cart_items:
        await callback.answer("⚠️ Savatingiz bo'sh, buyurtma bera olmaysiz!", show_alert=True)
        return

    await callback.message.delete()

    # Birinchi bosqichga o'tamiz: Ismni so'rash
    await callback.message.answer(
        "👤 Buyurtmani rasmiylashtirish uchun birinchi navbatda <b>Ism va Familiyangizni</b> kiriting:")
    await state.set_state(OrderSteps.waiting_for_name)
    await callback.answer()


# 2. ISM QABUL QILINGANDA
@router.message(OrderSteps.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    if len(message.text) < 3:
        await message.answer("⚠️ Iltimos, ismingizni to'liqroq kiriting (kamida 3 ta harf):")
        return

    # Ismni xotiraga saqlaymiz
    await state.update_data(full_name=message.text)

    # Telefon raqamini so'rash va pastdan kontakt yuborish tugmasini chiqarish
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Telefon raqamni yuborish", request_contact=True)

    await message.answer(
        "📞 Rahmat! Endi esa <b>Telefon raqamingizni</b> pastdagi tugmani bosish orqali yuboring yoki qo'lda kiriting (Masalan: +998901234567):",
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True)
    )
    await state.set_state(OrderSteps.waiting_for_phone)


# 3. TELEFON RAQAM QABUL QILINGANDA (TUGMA YOKI MATN ORQALI)
@router.message(OrderSteps.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    # Agar tugma orqali yuborilgan bo'lsa contact ichidan oladi, bo'lmasa matndan
    if message.contact:
        phone_number = message.contact.phone_number
    else:
        phone_number = message.text
        if not phone_number.startswith('+') and not phone_number.isdigit():
            await message.answer("⚠️ Iltimos, telefon raqamingizni to'g'ri formatda kiriting:")
            return

    await state.update_data(phone_number=phone_number)

    # Manzilni so'rash (Klaviatura tugmasini yo'qotamiz ReplyKeyboardRemove orqali)
    await message.answer(
        "📍 Oxirgi qadam! Kitoblar yetkazib berilishi kerak bo'lgan <b>To'liq manzilingizni</b> kiriting (Viloyat, tuman, ko'cha, uy raqami):",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(OrderSteps.waiting_for_address)


# 4. MANZIL QABUL QILINGANDA VA BUYURTMANI YAKUNLASH
@router.message(OrderSteps.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    address = message.text
    user_id = message.from_user.id

    # Xotiradagi barcha yig'ilgan ma'lumotlarni o'qiymiz
    user_data = await state.get_data()
    full_name = user_data.get("full_name")
    phone_number = user_data.get("phone_number")

    cart_items = await get_user_cart_items(user_id)

    # Bazada buyurtmani rasmiylashtiramiz
    order = await create_order_in_db(
        user_id=user_id,
        full_name=full_name,
        phone_number=phone_number,
        address=address,
        cart_items=cart_items
    )

    # Foydalanuvchiga muvaffaqiyatli yakun xabarini ko'rsatamiz
    success_text = (
        f"🎉 <b>Buyurtmangiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"🆔 <b>Buyurtma raqami:</b> #{order.id}\n"
        f"👤 <b>Mijoz:</b> {full_name}\n"
        f"📞 <b>Telefon:</b> {phone_number}\n"
        f"📍 <b>Manzil:</b> {address}\n"
        f"💵 <b>Umumiy summa:</b> {order.total_price} so'm\n\n"
        f"⏱ Tez orada operatorlarimiz siz bilan bog'lanishadi. Xaridingiz uchun rahmat!"
    )

    # Asosiy menyu tugmalarini qaytaramiz
    builder = ReplyKeyboardBuilder()
    builder.button(text="📚 Kitoblar katalogi")
    builder.button(text="🛒 Savatni ko'rish")
    builder.button(text="ℹ️ Biz haqimizda")
    builder.adjust(1, 1, 1)

    await message.answer(text=success_text, parse_mode="HTML", reply_markup=builder.as_markup(resize_keyboard=True))

    # FSM holatini tozalaymiz (Xotirani bo'shatamiz)
    await state.clear()
