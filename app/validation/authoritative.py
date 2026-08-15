import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Customer, CustomerProductPrice, DraftOrder, Product
from app.schemas import PurchaseOrder, ValidationResult
from app.services.rag import normalize


async def validate_authoritative_data(
    session: AsyncSession, order: PurchaseOrder, settings: Settings, run_id: str
) -> list[ValidationResult]:
    results: list[ValidationResult] = []
    customer = (
        await session.get(Customer, order.resolved_customer_id)
        if order.resolved_customer_id
        else None
    )
    results.append(
        ValidationResult(
            code="CUSTOMER_RESOLVED",
            passed=customer is not None and customer.active,
            message=(
                f"Resolved customer {customer.canonical_name}"
                if customer
                else "Customer could not be resolved to an active record"
            ),
        )
    )
    if customer:
        supplied_address = normalize(order.shipping_address)
        address_passed = any(
            normalize(address) in supplied_address or supplied_address in normalize(address)
            for address in customer.approved_shipping_addresses
            if supplied_address
        )
        results.append(
            ValidationResult(
                code="APPROVED_SHIPPING_ADDRESS",
                passed=address_passed,
                message=(
                    "Shipping address matches an approved customer location"
                    if address_passed
                    else "Shipping address is not an approved customer location"
                ),
            )
        )
        expected_days = re.search(r"\d+", customer.payment_terms or "")
        supplied_days = re.search(r"\d+", order.payment_terms or "")
        terms_passed = bool(
            expected_days and supplied_days and expected_days.group() == supplied_days.group()
        )
        results.append(
            ValidationResult(
                code="PAYMENT_TERMS_MATCH",
                passed=terms_passed,
                message=(
                    f"Expected {customer.payment_terms}; "
                    f"received {order.payment_terms or 'missing'}"
                ),
            )
        )
    for index, item in enumerate(order.line_items, start=1):
        product = await session.get(Product, item.resolved_sku) if item.resolved_sku else None
        results.append(
            ValidationResult(
                code=f"LINE_{index}_PRODUCT_RESOLVED",
                passed=product is not None and product.active,
                message=(
                    f"Resolved to {product.sku} - {product.name}"
                    if product
                    else f"Line {index} could not be resolved to an active product"
                ),
            )
        )
        if customer and product and order.currency and item.unit_price is not None:
            contract = await session.scalar(
                select(CustomerProductPrice).where(
                    CustomerProductPrice.customer_id == customer.id,
                    CustomerProductPrice.sku == product.sku,
                    CustomerProductPrice.currency == order.currency,
                    CustomerProductPrice.active.is_(True),
                )
            )
            expected_price = contract.unit_price if contract else product.standard_unit_price
            if expected_price is not None:
                tolerance = expected_price * Decimal(
                    str(settings.price_tolerance_percent / 100)
                )
                results.append(
                    ValidationResult(
                        code=f"LINE_{index}_PRICE_MATCH",
                        passed=abs(item.unit_price - expected_price) <= tolerance,
                        message=(
                            f"Expected {order.currency} {expected_price}; "
                            f"received {item.unit_price}"
                        ),
                    )
                )
    if customer and order.po_number:
        duplicate = await session.scalar(
            select(DraftOrder).where(
                DraftOrder.customer_id == customer.id,
                DraftOrder.po_number == order.po_number,
                DraftOrder.run_id != run_id,
            )
        )
        results.append(
            ValidationResult(
                code="UNIQUE_PO_NUMBER",
                passed=duplicate is None,
                message=(
                    "PO number has not previously been processed"
                    if duplicate is None
                    else f"PO number already exists as draft order {duplicate.id}"
                ),
            )
        )
    return results
