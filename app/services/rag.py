import logging
import re
from typing import Any

from langsmith import trace
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Customer, KnowledgeChunk, KnowledgeDocument, Product
from app.schemas import EnrichmentResult, PurchaseOrder, RAGMatch

logger = logging.getLogger(__name__)


def normalize(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def matches_product_reference(
    product: Product, raw_sku: str | None, description: str | None
) -> bool:
    references = {normalize(raw_sku), normalize(description)} - {""}
    known_values = {
        normalize(product.sku),
        normalize(product.name),
        *(normalize(alias) for alias in product.aliases),
    }
    return bool(references & known_values)


class EmbeddingService:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self._client = client

    def _client_or_raise(self) -> Any:
        if self._client is None:
            if self.settings.openai_api_key is None:
                raise RuntimeError("OPENAI_API_KEY is required for RAG embeddings")
            self._client = AsyncOpenAI(
                api_key=self.settings.openai_api_key.get_secret_value(),
                timeout=self.settings.openai_timeout_seconds,
                max_retries=2,
            )
        return self._client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        logger.info(
            "embedding_started model=%s inputs=%s", self.settings.embedding_model, len(texts)
        )
        async with trace(
            "openai.embeddings.create",
            run_type="llm",
            inputs={"model": self.settings.embedding_model, "input_count": len(texts)},
            tags=["embedding", "rag"],
            metadata={
                "ls_provider": "openai",
                "ls_model_name": self.settings.embedding_model,
            },
        ) as embedding_run:
            response = await self._client_or_raise().embeddings.create(
                model=self.settings.embedding_model,
                input=texts,
                dimensions=self.settings.embedding_dimensions,
                encoding_format="float",
            )
            vectors = [item.embedding for item in response.data]
            embedding_run.end(
                outputs={"vector_count": len(vectors)},
                metadata={
                    "usage": (
                        response.usage.model_dump(mode="json")
                        if getattr(response, "usage", None) is not None
                        else None
                    )
                },
            )
        logger.info("embedding_completed vectors=%s", len(vectors))
        return vectors


class RAGService:
    def __init__(self, settings: Settings, embeddings: EmbeddingService | None = None) -> None:
        self.settings = settings
        self.embeddings = embeddings or EmbeddingService(settings)

    async def search(
        self, session: AsyncSession, query: str, entity_type: str, top_k: int | None = None
    ) -> list[RAGMatch]:
        vector = (await self.embeddings.embed([query]))[0]
        distance = KnowledgeChunk.embedding.cosine_distance(vector).label("distance")
        statement = (
            select(KnowledgeChunk, KnowledgeDocument, distance)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(KnowledgeChunk.embedding.is_not(None))
            .where(KnowledgeChunk.chunk_metadata["entity_type"].as_string() == entity_type)
            .order_by(distance)
            .limit(top_k or self.settings.rag_top_k)
        )
        rows = (await session.execute(statement)).all()
        matches = [
            RAGMatch(
                query=query,
                entity_type=entity_type,
                entity_id=chunk.chunk_metadata.get("entity_id"),
                entity_name=chunk.chunk_metadata.get("entity_name"),
                similarity=max(-1.0, min(1.0, 1.0 - float(row_distance))),
                chunk_id=chunk.id,
                source_title=document.title,
                content=chunk.content,
            )
            for chunk, document, row_distance in rows
        ]
        logger.info(
            "rag_search_completed entity_type=%s query_characters=%s matches=%s top_similarity=%s",
            entity_type,
            len(query),
            len(matches),
            f"{matches[0].similarity:.3f}" if matches else "none",
        )
        return matches

    async def enrich(self, session: AsyncSession, order: PurchaseOrder) -> EnrichmentResult:
        enriched = order.model_copy(deep=True)
        all_matches: list[RAGMatch] = []

        customer_query = f"Customer organization: {order.customer_name or 'unknown'}"
        customer_matches = await self.search(session, customer_query, "customer")
        all_matches.extend(customer_matches)

        exact_customer = None
        if order.customer_name:
            candidates = (
                await session.scalars(select(Customer).where(Customer.active.is_(True)))
            ).all()
            wanted = normalize(order.customer_name)
            exact_customer = next(
                (
                    customer
                    for customer in candidates
                    if wanted
                    in {
                        normalize(customer.canonical_name),
                        *(normalize(x) for x in customer.aliases),
                    }
                ),
                None,
            )
        selected_customer_id = exact_customer.id if exact_customer else None
        if not selected_customer_id and customer_matches:
            best = customer_matches[0]
            if best.similarity >= self.settings.rag_match_threshold:
                selected_customer_id = best.entity_id
        enriched.resolved_customer_id = selected_customer_id

        products = (await session.scalars(select(Product).where(Product.active.is_(True)))).all()
        for index, item in enumerate(enriched.line_items):
            query = (
                f"Product SKU or alias: {item.raw_sku or 'missing'}; "
                f"description: {item.raw_description or 'missing'}"
            )
            matches = await self.search(session, query, "product")
            all_matches.extend(matches)
            exact_product = next(
                (
                    product
                    for product in products
                    if matches_product_reference(
                        product, item.raw_sku, item.raw_description
                    )
                ),
                None,
            )
            if exact_product:
                item.resolved_sku = exact_product.sku
            elif matches and matches[0].similarity >= self.settings.rag_match_threshold:
                item.resolved_sku = matches[0].entity_id
            logger.info(
                "product_resolution line=%s raw_sku=%s resolved_sku=%s",
                index + 1,
                item.raw_sku,
                item.resolved_sku,
            )

        policy_query = (
            f"Purchase order acceptance rules for payment terms {order.payment_terms}; "
            f"currency {order.currency}; delivery address approval and pricing"
        )
        all_matches.extend(await self.search(session, policy_query, "policy", top_k=3))
        logger.info(
            "rag_enrichment_completed customer_id=%s resolved_products=%s/%s evidence=%s",
            enriched.resolved_customer_id,
            sum(item.resolved_sku is not None for item in enriched.line_items),
            len(enriched.line_items),
            len(all_matches),
        )
        return EnrichmentResult(order=enriched, matches=all_matches)
