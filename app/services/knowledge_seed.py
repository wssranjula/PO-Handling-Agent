import logging
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import (
    Customer,
    CustomerProductPrice,
    KnowledgeChunk,
    KnowledgeDocument,
    Product,
)
from app.services.rag import EmbeddingService

logger = logging.getLogger(__name__)


CUSTOMERS = [
    {
        "id": "CUST-NORTHSTAR",
        "canonical_name": "Northstar Home Stores",
        "aliases": ["Northstar Stores", "Northstar Home"],
        "approved_shipping_addresses": [
            "Northstar Home Stores - Central Warehouse, Warehouse 4, 18 Harbour Road, "
            "Colombo 01, Sri Lanka, Attention: Receiving Desk"
        ],
        "payment_terms": "Net 45",
    },
    {
        "id": "CUST-ACME",
        "canonical_name": "Acme Retail",
        "aliases": ["Acme Retail Ltd", "Acme Retail (Pvt) Ltd"],
        "approved_shipping_addresses": ["Dock 2, 55 Lake Avenue, Kandy, Sri Lanka"],
        "payment_terms": "Net 30",
    },
]

PRODUCTS = [
    {
        "sku": "THERM-16-BLUE",
        "name": "Blue insulated drink bottle - 16 oz",
        "aliases": ["blue-therm16", "blue thermal bottle", "blue bottle 16oz"],
        "standard_unit_price": "18.50",
    },
    {
        "sku": "LID-SPARE-16",
        "name": "Replacement lid for 16 oz insulated bottle",
        "aliases": ["lid spare", "replacement bottle lid", "spare thermos lid"],
        "standard_unit_price": "2.00",
    },
    {
        "sku": "MUG-WHITE-STD",
        "name": "White ceramic mug, retail boxed",
        "aliases": ["MUG-WHT", "white mug", "ceramic mug white"],
        "standard_unit_price": "7.50",
    },
]

CONTRACT_PRICES = [
    ("CUST-NORTHSTAR", "THERM-16-BLUE", "USD", "18.50"),
    ("CUST-NORTHSTAR", "LID-SPARE-16", "USD", "2.00"),
    ("CUST-NORTHSTAR", "MUG-WHITE-STD", "USD", "7.50"),
    ("CUST-ACME", "MUG-WHITE-STD", "USD", "7.50"),
]


async def seed_knowledge(session: AsyncSession, settings: Settings) -> dict[str, int]:
    for values in CUSTOMERS:
        customer = await session.get(Customer, values["id"])
        if customer is None:
            customer = Customer(**values)
            session.add(customer)
        else:
            for key, value in values.items():
                setattr(customer, key, value)

    for values in PRODUCTS:
        product = await session.get(Product, values["sku"])
        if product is None:
            product = Product(**values)
            session.add(product)
        else:
            for key, value in values.items():
                setattr(product, key, value)
    await session.flush()

    for customer_id, sku, currency, price in CONTRACT_PRICES:
        contract = await session.scalar(
            select(CustomerProductPrice).where(
                CustomerProductPrice.customer_id == customer_id,
                CustomerProductPrice.sku == sku,
                CustomerProductPrice.currency == currency,
            )
        )
        if contract is None:
            session.add(
                CustomerProductPrice(
                    customer_id=customer_id,
                    sku=sku,
                    currency=currency,
                    unit_price=price,
                )
            )
        else:
            contract.unit_price = price
            contract.active = True

    root = Path("knowledge_base").resolve()
    chunk_specs: list[dict] = []
    for customer in CUSTOMERS:
        chunk_specs.append(
            {
                "source": root / "customers.md",
                "title": "Approved customer directory",
                "document_type": "customer_directory",
                "content": (
                    f"Customer {customer['canonical_name']} ({customer['id']}). "
                    f"Aliases: {', '.join(customer['aliases'])}. Approved delivery addresses: "
                    f"{'; '.join(customer['approved_shipping_addresses'])}. "
                    f"Payment terms: {customer['payment_terms']}."
                ),
                "metadata": {
                    "entity_type": "customer",
                    "entity_id": customer["id"],
                    "entity_name": customer["canonical_name"],
                },
            }
        )
    for product in PRODUCTS:
        chunk_specs.append(
            {
                "source": root / "products.md",
                "title": "Product catalog and aliases",
                "document_type": "product_catalog",
                "content": (
                    f"Product {product['sku']}: {product['name']}. "
                    f"Known aliases and customer wording: {', '.join(product['aliases'])}. "
                    f"Standard unit price: USD {product['standard_unit_price']}."
                ),
                "metadata": {
                    "entity_type": "product",
                    "entity_id": product["sku"],
                    "entity_name": product["name"],
                },
            }
        )
    policy_path = root / "order-acceptance-policy.md"
    policy_text = policy_path.read_text(encoding="utf-8")
    for index, paragraph in enumerate(
        part.strip()
        for part in policy_text.split("\n\n")
        if part.strip() and not part.startswith("#")
    ):
        chunk_specs.append(
            {
                "source": policy_path,
                "title": "Purchase order acceptance policy",
                "document_type": "policy",
                "content": paragraph,
                "metadata": {
                    "entity_type": "policy",
                    "entity_id": f"PO-POLICY-{index + 1}",
                    "entity_name": "Purchase order acceptance policy",
                },
            }
        )

    source_paths = {str(spec["source"]) for spec in chunk_specs}
    existing_documents = (
        await session.scalars(
            select(KnowledgeDocument).where(KnowledgeDocument.source_path.in_(source_paths))
        )
    ).all()
    if existing_documents:
        document_ids = [document.id for document in existing_documents]
        await session.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id.in_(document_ids))
        )
        await session.execute(
            delete(KnowledgeDocument).where(KnowledgeDocument.id.in_(document_ids))
        )
        await session.flush()

    embeddings = await EmbeddingService(settings).embed([spec["content"] for spec in chunk_specs])
    documents: dict[str, KnowledgeDocument] = {}
    indices: dict[str, int] = {}
    for spec, vector in zip(chunk_specs, embeddings, strict=True):
        source_path = str(spec["source"])
        document = documents.get(source_path)
        if document is None:
            document = KnowledgeDocument(
                title=spec["title"],
                document_type=spec["document_type"],
                source_path=source_path,
                version="1",
            )
            session.add(document)
            await session.flush()
            documents[source_path] = document
            indices[source_path] = 0
        chunk_index = indices[source_path]
        session.add(
            KnowledgeChunk(
                document_id=document.id,
                chunk_index=chunk_index,
                content=spec["content"],
                chunk_metadata=spec["metadata"],
                embedding=vector,
            )
        )
        indices[source_path] += 1

    await session.commit()
    counts = {
        "customers": len(CUSTOMERS),
        "products": len(PRODUCTS),
        "contract_prices": len(CONTRACT_PRICES),
        "documents": len(documents),
        "chunks": len(chunk_specs),
    }
    logger.info("knowledge_seed_completed counts=%s", counts)
    return counts
