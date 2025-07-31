import factory
from factory import fuzzy
from django.contrib.auth import get_user_model
from apps.products.models import Product, Category, ProductStock
from apps.reservations.models import Reservation, ReservationStatus
from decimal import Decimal

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user{n}')
    email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Faker('word')
    slug = factory.LazyAttribute(lambda obj: obj.name.lower())


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Faker('sentence', nb_words=3)
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(' ', '-'))
    description = factory.Faker('text')
    category = factory.SubFactory(CategoryFactory)
    price = fuzzy.FuzzyDecimal(10.0, 1000.0, 2)
    sku = factory.Sequence(lambda n: f'SKU-{n:06d}')
    is_active = True


class ProductStockFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductStock

    product = factory.SubFactory(ProductFactory)
    quantity = fuzzy.FuzzyInteger(0, 100)
    reserved_quantity = 0


class ReservationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reservation

    user = factory.SubFactory(UserFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = fuzzy.FuzzyInteger(1, 10)
    status = ReservationStatus.PENDING
    price_per_item = factory.LazyAttribute(lambda obj: obj.product.price)
    total_price = factory.LazyAttribute(lambda obj: obj.price_per_item * obj.quantity)