from app.models import Product
from app.services.rag import matches_product_reference, normalize


def test_normalize_supports_customer_and_sku_alias_matching() -> None:
    assert normalize("Northstar Home Stores (Pvt) Ltd") == "northstarhomestorespvtltd"
    assert normalize("blue-therm16") == normalize("BLUE THERM 16")


def test_product_alias_can_be_supplied_as_description() -> None:
    product = Product(
        sku="THERM-16-BLUE",
        name="Blue insulated drink bottle - 16 oz",
        aliases=["blue-therm16", "blue thermal bottle"],
        active=True,
    )

    assert matches_product_reference(product, None, "blue thermal bottle")
