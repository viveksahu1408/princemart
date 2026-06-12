from django.core.management.base import BaseCommand
from store.models import Product, ProductVariant

class Command(BaseCommand):
    help = '700+ products ke liye unki unit ke hisab se default active variants (Stock: 20) create karega.'

    def handle(self, *args, **kwargs):
        products = Product.objects.all()
        created_count = 0
        skipped_count = 0

        self.stdout.write(self.style.SUCCESS(f'Total {products.count()} products ko scan kiya ja raha hai...'))

        for product in products:
            # Check karenge ki kya is product ka pehle se koi variant hai
            # Agar tumhare model me related_name='variants' nahi hai, toh productvariant_set.exists() use hoga
            has_variant = False
            try:
                has_variant = product.variants.exists()
            except AttributeError:
                has_variant = product.productvariant_set.exists()

            if not has_variant:
                # Product ki unit ke hisab se saaf-suthra naam set karenge
                product_unit = str(product.unit).strip().lower() if product.unit else 'pieces'
                
                if 'packet' in product_unit:
                    variant_name = '1 Packet'
                elif 'kilogram' in product_unit or 'kg' in product_unit:
                    variant_name = '1 Kg'
                elif 'liter' in product_unit or 'ltr' in product_unit:
                    variant_name = '1 Ltr'
                else:
                    variant_name = '1 Pcs'

                # Default Variant create karenge (Stock strictly 20)
                # Agar model me productvariant_set chal raha hai toh naye object me field names verify kar lena
                try:
                    ProductVariant.objects.create(
                        product=product,
                        weight_or_size=variant_name,
                        market_price=product.market_price,
                        selling_price=product.selling_price,
                        stock_quantity=20,  # Strict 20 pieces stock
                        is_active=True
                    )
                    created_count += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error product {product.name} me: {str(e)}'))
            else:
                skipped_count += 1

        self.stdout.write(self.style.SUCCESS(f'Kaam Khatam! 🎉 {created_count} products ke variants ban gaye. {skipped_count} products pehle se sahi the.'))