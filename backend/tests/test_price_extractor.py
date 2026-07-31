from backend.app.connectors.price_extractor import extract_price_info


def test_direct_price_confidence_when_model_is_nearby():
    result = extract_price_info("Apple iPhone 17 ab 749,90 € bei idealo.de", "https://www.idealo.de/iphone-17")

    assert result == {
        "price": 749.90,
        "currency": "EUR",
        "model": "iPhone 17",
        "source": "https://www.idealo.de/iphone-17",
        "confidence": "direct",
    }


def test_indirect_price_confidence_when_model_is_not_nearby():
    result = extract_price_info("Preisvergleich Deutschland. Bereits ab 899,00 €.", "https://www.idealo.de/ps5-pro")

    assert result["price"] == 899.00
    assert result["currency"] == "EUR"
    assert result["model"] == "PlayStation 5 Pro"
    assert result["confidence"] == "indirect"


def test_no_price_returns_none_confidence():
    result = extract_price_info("PlayStation 5 Pro im Preisvergleich", "https://www.idealo.de/ps5-pro")

    assert result["price"] is None
    assert result["currency"] == "EUR"
    assert result["confidence"] == "none"


def test_european_thousands_and_decimal_formats():
    first = extract_price_info("iPhone 17 Pro ab 1.099,99 €", "https://www.idealo.de/iphone-17-pro")
    second = extract_price_info("PS5 Pro kostet € 899,00", "https://www.idealo.de/ps5-pro")

    assert first["price"] == 1099.99
    assert second["price"] == 899.00

