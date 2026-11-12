from django.contrib import admin
from django.utils.safestring import mark_safe

from books.models import Category, Book, Cart


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display=('name','slug','get_books_count',)
    prepopulated_fields={'slug':('name',)}
    search_fields=('name',)

    def get_books_count(self,obj):
        return obj.books.count()
    get_books_count.short_description="Kitoblar soni"

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display=('get_image','title','author','category','price','discount_price','stock','is_available')
    list_editable=('price','discount_price','stock','is_available')
    list_filter=('category','is_available','language','cover_type','created_at')
    search_fields=('title','author','isbn')

    fieldsets=(
    ("Asosiy ma'lumotlar",{
        'fields':('title','author','category','description',
                  ('image','get_image_preview'))
    }),
    ("Narx va sotuv",{
        'fields':('price','discount_price','stock','is_available')
    }),
    ("Qo'shimcha xarakteristikalar",{
        'fields':('pages','language','cover_type','published_year','isbn'),'classes':('collapse',)
    }),
    )

    readonly_fields=('get_image_preview',)

    def get_image(self,obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="45" height="60" style="object-fit:cover; border-radius:4px;"/>')
        return "Rasm yo'q"
    get_image.short_description="Muqova"

    def get_image_preview(self,obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="150" style="border-radius:8px;"/>')
        return "Rasm yuklanmagan"
    get_image_preview.short_description="Hozirgi muqova"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'book', 'quantity', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user_id', 'book__title')


from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('book', 'quantity', 'price')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone_number', 'total_price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    list_editable = ('status',)
    search_fields = ('full_name', 'phone_number', 'id')
    inlines = [OrderItemInline]
