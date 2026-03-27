"""
Seed script: creates 30 mock products across the seeded categories.
Idempotent — skips products whose name_es already exists.
Run after seed.py so categories are present.
"""
import asyncio
import os
import sys
from decimal import Decimal

project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)
os.chdir(project_root)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select

from app.config import settings
from app.models.category import Category
from app.models.product import Product

PRODUCTS = [
    # Cestas / Baskets
    {
        "name_es": "Cesta de mimbre natural",
        "name_en": "Natural wicker basket",
        "description_es": "Cesta artesanal tejida a mano con mimbre natural. Perfecta para almacenamiento decorativo.",
        "description_en": "Handwoven artisan basket made from natural wicker. Perfect for decorative storage.",
        "price": Decimal("4500.00"),
        "category_slug": "baskets",
    },
    {
        "name_es": "Cesta redonda con tapa",
        "name_en": "Round basket with lid",
        "description_es": "Cesta redonda con tapa tejida en fibra natural. Ideal para organizar el hogar.",
        "description_en": "Round lidded basket woven in natural fiber. Ideal for home organization.",
        "price": Decimal("5800.00"),
        "category_slug": "baskets",
    },
    {
        "name_es": "Cesta de palma trenzada",
        "name_en": "Braided palm basket",
        "description_es": "Cesta pequeña elaborada con palma trenzada, con terminaciones en cuero natural.",
        "description_en": "Small basket crafted from braided palm with natural leather finishing.",
        "price": Decimal("3200.00"),
        "category_slug": "baskets",
    },
    {
        "name_es": "Cesta porta plantas",
        "name_en": "Plant holder basket",
        "description_es": "Cesta alta en mimbre para macetas, con base reforzada y diseño minimalista.",
        "description_en": "Tall wicker plant holder with reinforced base and minimalist design.",
        "price": Decimal("6200.00"),
        "category_slug": "baskets",
    },
    {
        "name_es": "Set de cestas anidadas",
        "name_en": "Nesting basket set",
        "description_es": "Juego de tres cestas anidadas en distintos tamaños, tejidas en paja natural.",
        "description_en": "Set of three nesting baskets in different sizes, woven from natural straw.",
        "price": Decimal("9800.00"),
        "category_slug": "baskets",
    },
    {
        "name_es": "Cesta de compras con asas",
        "name_en": "Market basket with handles",
        "description_es": "Cesta de mercado de fibra natural con asas de cuero. Resistente y elegante.",
        "description_en": "Natural fiber market basket with leather handles. Durable and elegant.",
        "price": Decimal("7500.00"),
        "category_slug": "baskets",
    },
    # Cerámica / Ceramics
    {
        "name_es": "Tazón de cerámica artesanal",
        "name_en": "Artisan ceramic bowl",
        "description_es": "Tazón hecho a mano en cerámica esmaltada. Apto para uso diario y lavavajillas.",
        "description_en": "Handmade glazed ceramic bowl. Dishwasher safe and suitable for daily use.",
        "price": Decimal("3800.00"),
        "category_slug": "ceramics",
    },
    {
        "name_es": "Jarra de cerámica rústica",
        "name_en": "Rustic ceramic pitcher",
        "description_es": "Jarra de cerámica con acabado rústico y esmalte interior. Capacidad 1 litro.",
        "description_en": "Ceramic pitcher with rustic finish and interior glaze. 1 liter capacity.",
        "price": Decimal("5200.00"),
        "category_slug": "ceramics",
    },
    {
        "name_es": "Set de tazas de café",
        "name_en": "Coffee cup set",
        "description_es": "Set de 4 tazas de café en cerámica artesanal con plato. Colores terrosos.",
        "description_en": "Set of 4 handcrafted ceramic coffee cups with saucers. Earthy tones.",
        "price": Decimal("8900.00"),
        "category_slug": "ceramics",
    },
    {
        "name_es": "Plato hondo de barro",
        "name_en": "Deep clay plate",
        "description_es": "Plato hondo de barro cocido a alta temperatura. Textura natural única en cada pieza.",
        "description_en": "High-fired clay deep plate. Unique natural texture in every piece.",
        "price": Decimal("2900.00"),
        "category_slug": "ceramics",
    },
    {
        "name_es": "Maceta de cerámica pintada",
        "name_en": "Painted ceramic pot",
        "description_es": "Maceta de cerámica con diseños geométricos pintados a mano. Con orificio de drenaje.",
        "description_en": "Ceramic pot with hand-painted geometric designs. Includes drainage hole.",
        "price": Decimal("4100.00"),
        "category_slug": "ceramics",
    },
    {
        "name_es": "Fuente ovalada de cerámica",
        "name_en": "Oval ceramic serving dish",
        "description_es": "Fuente ovalada para servir en cerámica blanca mate. Ideal para mesa compartida.",
        "description_en": "Matte white ceramic oval serving dish. Perfect for shared table settings.",
        "price": Decimal("6700.00"),
        "category_slug": "ceramics",
    },
    # Textiles / Textiles
    {
        "name_es": "Mantel de lino natural",
        "name_en": "Natural linen tablecloth",
        "description_es": "Mantel de lino 100% natural, lavable. Disponible en 150x200 cm.",
        "description_en": "100% natural linen tablecloth, washable. Available in 150x200 cm.",
        "price": Decimal("7200.00"),
        "category_slug": "textiles",
    },
    {
        "name_es": "Camino de mesa tejido",
        "name_en": "Woven table runner",
        "description_es": "Camino de mesa tejido en algodón con flecos naturales. 40x150 cm.",
        "description_en": "Woven cotton table runner with natural fringe. 40x150 cm.",
        "price": Decimal("3500.00"),
        "category_slug": "textiles",
    },
    {
        "name_es": "Almohadón de lana",
        "name_en": "Wool cushion cover",
        "description_es": "Funda de almohadón tejida en lana merino con relleno incluido. 45x45 cm.",
        "description_en": "Merino wool cushion cover with filling included. 45x45 cm.",
        "price": Decimal("5600.00"),
        "category_slug": "textiles",
    },
    {
        "name_es": "Servilletas de algodón set x6",
        "name_en": "Cotton napkins set of 6",
        "description_es": "Set de 6 servilletas de algodón orgánico con bordado artesanal en el borde.",
        "description_en": "Set of 6 organic cotton napkins with handcrafted embroidery on the edge.",
        "price": Decimal("4400.00"),
        "category_slug": "textiles",
    },
    {
        "name_es": "Manta de telar artesanal",
        "name_en": "Handloom throw blanket",
        "description_es": "Manta tejida en telar artesanal con lana de oveja. Tonos naturales y cálidos.",
        "description_en": "Blanket woven on a handloom with sheep's wool. Natural warm tones.",
        "price": Decimal("12500.00"),
        "category_slug": "textiles",
    },
    {
        "name_es": "Porta vajilla bordado",
        "name_en": "Embroidered dish towel",
        "description_es": "Repasador de cocina en lino bordado a mano con motivos florales.",
        "description_en": "Kitchen linen dish towel hand-embroidered with floral motifs.",
        "price": Decimal("2200.00"),
        "category_slug": "textiles",
    },
    # Joyería / Jewelry
    {
        "name_es": "Collar de piedras naturales",
        "name_en": "Natural stone necklace",
        "description_es": "Collar largo con piedras semi preciosas en tonos tierra, hilo de seda.",
        "description_en": "Long necklace with semi-precious stones in earth tones, silk thread.",
        "price": Decimal("6800.00"),
        "category_slug": "jewelry",
    },
    {
        "name_es": "Aros de bronce martillado",
        "name_en": "Hammered bronze earrings",
        "description_es": "Aros grandes de bronce martillado a mano. Acabado oxidado natural.",
        "description_en": "Large hand-hammered bronze earrings. Natural oxidized finish.",
        "price": Decimal("4200.00"),
        "category_slug": "jewelry",
    },
    {
        "name_es": "Pulsera trenzada de cuero",
        "name_en": "Braided leather bracelet",
        "description_es": "Pulsera de cuero curtido al vegetal, trenzado a mano con cierre de plata.",
        "description_en": "Vegetable-tanned leather bracelet, hand-braided with silver clasp.",
        "price": Decimal("3100.00"),
        "category_slug": "jewelry",
    },
    {
        "name_es": "Anillo de plata con turquesa",
        "name_en": "Silver ring with turquoise",
        "description_es": "Anillo de plata 925 con piedra turquesa natural incrustada. Talla ajustable.",
        "description_en": "925 silver ring with inlaid natural turquoise stone. Adjustable size.",
        "price": Decimal("8500.00"),
        "category_slug": "jewelry",
    },
    {
        "name_es": "Gargantilla de semillas",
        "name_en": "Seed choker necklace",
        "description_es": "Gargantilla elaborada con semillas naturales y cuentas de madera. Artesanía norteña.",
        "description_en": "Choker made with natural seeds and wooden beads. Northern craftsmanship.",
        "price": Decimal("2800.00"),
        "category_slug": "jewelry",
    },
    {
        "name_es": "Set collar y aros plata",
        "name_en": "Silver necklace and earrings set",
        "description_es": "Set de collar y aros en plata 925 con diseño geométrico minimalista.",
        "description_en": "925 silver necklace and earrings set with minimalist geometric design.",
        "price": Decimal("14200.00"),
        "category_slug": "jewelry",
    },
    # Decoración / Decor
    {
        "name_es": "Vela artesanal de cera de soja",
        "name_en": "Artisan soy wax candle",
        "description_es": "Vela de cera de soja con esencias naturales de lavanda y cedro. 200 g.",
        "description_en": "Soy wax candle with natural lavender and cedar essences. 200 g.",
        "price": Decimal("3400.00"),
        "category_slug": "decor",
    },
    {
        "name_es": "Marco de madera rústico",
        "name_en": "Rustic wooden frame",
        "description_es": "Marco de madera recuperada para fotos 15x20 cm. Sin barniz, acabado natural.",
        "description_en": "Reclaimed wood frame for 15x20 cm photos. Unvarnished, natural finish.",
        "price": Decimal("2600.00"),
        "category_slug": "decor",
    },
    {
        "name_es": "Espejo con marco de mimbre",
        "name_en": "Wicker framed mirror",
        "description_es": "Espejo redondo de 40 cm con marco tejido en mimbre natural. Estilo boho.",
        "description_en": "Round 40 cm mirror with natural wicker woven frame. Boho style.",
        "price": Decimal("11500.00"),
        "category_slug": "decor",
    },
    {
        "name_es": "Porta velas de barro",
        "name_en": "Clay candle holder",
        "description_es": "Porta velas bajo en barro cocido con perforaciones caladas. Luz cálida tamizada.",
        "description_en": "Low clay candle holder with cut-out perforations. Warm filtered light.",
        "price": Decimal("2900.00"),
        "category_slug": "decor",
    },
    {
        "name_es": "Colgante de ramas y plumas",
        "name_en": "Branch and feather wall hanging",
        "description_es": "Colgante decorativo para pared con ramas naturales, plumas y hilo de algodón.",
        "description_en": "Decorative wall hanging with natural branches, feathers and cotton thread.",
        "price": Decimal("4800.00"),
        "category_slug": "decor",
    },
    {
        "name_es": "Difusor de caña natural",
        "name_en": "Natural reed diffuser",
        "description_es": "Difusor de ambiente con varillas de caña y fragancia de jazmín y sándalo. 100 ml.",
        "description_en": "Room diffuser with reed sticks and jasmine and sandalwood fragrance. 100 ml.",
        "price": Decimal("5100.00"),
        "category_slug": "decor",
    },
    {
        "name_es": "Bandeja de madera de quebracho",
        "name_en": "Quebracho wood tray",
        "description_es": "Bandeja rectangular en madera de quebracho pulida a mano. 30x20 cm.",
        "description_en": "Rectangular tray in hand-polished quebracho wood. 30x20 cm.",
        "price": Decimal("6300.00"),
        "category_slug": "decor",
    },
]


async def seed_products() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False, connect_args={"ssl": False})
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        # Load categories by slug
        result = await db.execute(select(Category))
        categories = {cat.slug: cat for cat in result.scalars().all()}

        if not categories:
            print("No categories found — run seed.py first.")
            return

        created = 0
        skipped = 0
        for p in PRODUCTS:
            result = await db.execute(select(Product).where(Product.name_es == p["name_es"]))
            if result.scalar_one_or_none() is not None:
                print(f"Skipping (exists): {p['name_es']}")
                skipped += 1
                continue

            category = categories.get(p["category_slug"])
            product = Product(
                name_es=p["name_es"],
                name_en=p["name_en"],
                description_es=p["description_es"],
                description_en=p["description_en"],
                price=p["price"],
                category_id=category.id if category else None,
                is_active=True,
            )
            db.add(product)
            print(f"Created: {p['name_en']}")
            created += 1

        await db.commit()
        print(f"\nDone — {created} created, {skipped} skipped.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_products())
