from django.core.cache import cache
from django.db import models

class Category(models.Model):
    name=models.CharField(max_length=100,verbose_name="Kategoriya nomi")
    slug=models.SlugField(max_length=100,unique=True)

    def __str__(self):
        return self.name

    def save(self,*args,**kwargs):
        super().save(*args,**kwargs)
        cache.delete('all_categories_cache')

    def delete(self,*args,**kwargs):
        super().delete(*args,**kwargs)
        cache.delete('all_categories_cache')

class Book(models.Model):
    title=models.CharField(max_length=200,verbose_name="Kitob nomi")
    author=models.CharField(max_length=150,verbose_name="Muallif")
    category=models.ForeignKey(Category,on_delete=models.CASCADE,related_name='books',verbose_name="Kategoriya")
    description=models.TextField(verbose_name="Kitob haqida qisqacha tavsif")
    image=models.ImageField(upload_to='books/',verbose_name="Kitob rasmi",null=True,blank=True)

    price=models.DecimalField(max_digits=10,decimal_places=2,verbose_name="Narxi")
    discount_price=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True,verbose_name="Chegirmadagi narxi")
    stock=models.PositiveIntegerField(default=0,verbose_name="Ombordagi soni")
    is_available=models.BooleanField(default=True,verbose_name="Sotuvda bormi?")

    pages=models.PositiveIntegerField(null=True,blank=True,verbose_name="Sahifalar soni")
    language=models.CharField(max_length=50,choices=[('uz',"O'zbekcha"),('ru',"Ruscha"),('en',"Inglizcha")],default=True,verbose_name="Tili")
    cover_type=models.CharField(max_length=50,choices=[('hard',"Qattiq"),('soft',"Yumshoq")],default='soft',verbose_name="Muqova turi")
    published_year=models.PositiveIntegerField(null=True,blank=True,verbose_name="Chop etilgan yili")
    isbn=models.CharField(max_length=13,unique=True,null=True,blank=True,verbose_name="ISBN kodi")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan vaqti")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return  f"{self.title}-{self.author}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete('all_products_cache')

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        cache.delete('all_products_cache')

    class Meta:
        verbose_name="Kitob"
        verbose_name_plural="Kitoblar"
        ordering=['-created_at']


class Cart(models.Model):
    user_id = models.BigIntegerField(verbose_name="Telegram User ID")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="carts", verbose_name="Kitob")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Soni")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Savat"
        verbose_name_plural = "Savatlar"
        # Bitta foydalanuvchi bitta kitobni faqat bir marta savatga qo'sha oladi (soni ko'payadi xolos)
        unique_together = ('user_id', 'book')

    def __str__(self):
        return f"User {self.user_id} - {self.book.title} ({self.quantity} ta)"


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Yangi'),
        ('confirmed', 'Tasdiqlangan'),
        ('delivered', 'Yuborilgan/Yetkazilgan'),
        ('canceled', 'Bekor qilingan'),
    ]

    user_id = models.BigIntegerField(verbose_name="Telegram User ID")
    full_name = models.CharField(max_length=255, verbose_name="Mijoz ismi")
    phone_number = models.CharField(max_length=50, verbose_name="Telefon raqami")
    address = models.TextField(verbose_name="Yetkazib berish manzili")
    total_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Umumiy summa")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Holati")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Buyurtma vaqti")

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"Buyurtma #{self.id} - {self.full_name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete('all_orders_cache')

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        cache.delete('all_orders_cache')


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Buyurtma")
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, verbose_name="Kitob")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Soni")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Sotilgan narxi")

    def __str__(self):
        return f"{self.book.title if self.book else 'O\'chirilgan kitob'} ({self.quantity} ta)"

