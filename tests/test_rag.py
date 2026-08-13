from app.services.rag import normalize


def test_normalize_supports_customer_and_sku_alias_matching() -> None:
    assert normalize("Northstar Home Stores (Pvt) Ltd") == "northstarhomestorespvtltd"
    assert normalize("blue-therm16") == normalize("BLUE THERM 16")
