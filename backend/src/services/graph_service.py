import json
import logging
from typing import Any

from ..db.repositories.graph_repo import GraphRepository
from ..models.embeddings import get_embeddings
from ..utils.url import url_to_id, name_to_id

logger = logging.getLogger(__name__)


class GraphService:
    def __init__(self, db: Any):
        self.db = db
        self.graph_repo = GraphRepository(db)

    # ── Entity storage with embeddings ──

    async def store_entities(
        self, company_url: str, entities: list[dict],
    ) -> dict[str, int]:
        """Store extracted entities as graph nodes with text embeddings and create relations."""
        company_id = url_to_id(company_url)
        counts: dict[str, int] = {}

        for entity in entities:
            etype = entity.get("type", "unknown")
            name = entity.get("name", "")
            attrs = entity.get("attributes", {})
            if not name:
                continue

            entity_id = name_to_id(f"{etype}_{name}")
            table = etype  # person, risk, certification, company

            # Build text for embedding from entity attributes
            text_for_embed = f"{name}. {json.dumps(attrs)}"
            try:
                embedding = get_embeddings().embed_query(text_for_embed)
            except Exception as e:
                logger.warning("Failed to embed entity %s: %s", name, e)
                embedding = None

            # Upsert entity node
            node_data = {
                "name": name,
                "entity_type": etype,
                **attrs,
            }
            if embedding:
                node_data["text_embedding"] = embedding
            await self.db.upsert(f"{table}:{entity_id}", node_data)

            # Create relation from company to entity
            relation = _entity_type_to_relation(etype)
            if relation:
                try:
                    await self.graph_repo.create_relation(
                        "company", company_id, relation, table, entity_id,
                    )
                except Exception as e:
                    logger.warning("Failed to create relation %s->%s: %s", company_id, entity_id, e)

            counts[etype] = counts.get(etype, 0) + 1

        logger.info("Stored %d entities for %s: %s", sum(counts.values()), company_url, counts)
        return counts

    # ── Embed the company profile itself ──

    async def embed_profile(self, company_url: str, profile: dict) -> None:
        """Store text embedding on the company node from its profile data."""
        company_id = url_to_id(company_url)
        profile_text = json.dumps(profile, default=str)[:8000]
        try:
            embedding = get_embeddings().embed_query(profile_text)
            await self.db.merge(f"company:{company_id}", {
                "text_embedding": embedding,
            })
            logger.info("Embedded profile for %s", company_url)
        except Exception as e:
            logger.warning("Failed to embed profile for %s: %s", company_url, e)

    # ── Compute graph embedding (average of neighbor text embeddings) ──

    async def compute_graph_embeddings(self, company_url: str) -> None:
        """Compute graph embedding for a company = average of its neighbors' text embeddings."""
        company_id = url_to_id(company_url)
        result = await self.db.query(
            "SELECT "
            "->works_at->person.text_embedding AS person_embeds, "
            "->has_risk->risk.text_embedding AS risk_embeds, "
            "->has_certification->certification.text_embedding AS cert_embeds, "
            "->supplies_to->company.text_embedding AS supplier_embeds "
            f"FROM company:{company_id}"
        )

        all_embeds = []
        if result and isinstance(result, list):
            row = result[0] if isinstance(result[0], dict) else (result[0].get("result", [{}])[0] if isinstance(result[0], dict) else {})
            # Handle SurrealDB response format
            if isinstance(result[0], dict) and "result" in result[0]:
                rows = result[0]["result"]
                row = rows[0] if rows else {}
            elif isinstance(result[0], dict):
                row = result[0]
            else:
                row = {}

            for key in ["person_embeds", "risk_embeds", "cert_embeds", "supplier_embeds"]:
                embeds = row.get(key, [])
                if isinstance(embeds, list):
                    for e in embeds:
                        if isinstance(e, list) and len(e) > 0:
                            all_embeds.append(e)

        if all_embeds:
            dim = len(all_embeds[0])
            avg = [sum(e[i] for e in all_embeds) / len(all_embeds) for i in range(dim)]
            await self.db.merge(f"company:{company_id}", {
                "graph_embedding": avg,
            })
            logger.info("Computed graph embedding for %s from %d neighbor embeddings", company_url, len(all_embeds))

    # ── Risk propagation ──

    async def compute_risk_score(self, company_url: str) -> dict[str, Any]:
        """Compute risk score based on graph traversal (risks on self + connected entities)."""
        company_id = url_to_id(company_url)

        # Direct risks
        result = await self.db.query(
            f"SELECT ->has_risk->risk.* AS direct_risks FROM company:{company_id}"
        )

        direct_risks = []
        if result and isinstance(result, list):
            row = _extract_row(result)
            direct_risks = row.get("direct_risks", [])
            if not isinstance(direct_risks, list):
                direct_risks = []

        # Supplier risks (2nd degree)
        supplier_result = await self.db.query(
            f"SELECT ->supplies_to->company->has_risk->risk.* AS supplier_risks "
            f"FROM company:{company_id}"
        )
        supplier_risks = []
        if supplier_result and isinstance(supplier_result, list):
            row = _extract_row(supplier_result)
            supplier_risks = row.get("supplier_risks", [])
            if not isinstance(supplier_risks, list):
                supplier_risks = []

        # Score: direct risks weighted 1.0, supplier risks weighted 0.5
        severity_weights = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
        score = 0.0

        for risk in direct_risks:
            if isinstance(risk, dict):
                sev = risk.get("severity", "medium").lower()
                score += severity_weights.get(sev, 0.5) * 1.0

        for risk in supplier_risks:
            if isinstance(risk, dict):
                sev = risk.get("severity", "medium").lower()
                score += severity_weights.get(sev, 0.5) * 0.5

        # Normalize to 0-1 range
        max_possible = max(1, len(direct_risks) + len(supplier_risks) * 0.5)
        normalized_score = min(score / max_possible, 1.0) if max_possible > 0 else 0.0

        risk_data = {
            "risk_score": round(normalized_score, 2),
            "direct_risk_count": len(direct_risks),
            "supplier_risk_count": len(supplier_risks),
            "direct_risks": _sanitize(direct_risks),
            "supplier_risks": _sanitize(supplier_risks),
        }

        # Store risk score on company node
        await self.db.merge(f"company:{company_id}", {
            "risk_score": risk_data["risk_score"],
        })

        return risk_data

    # ── GraphRAG retrieval ──

    async def graph_rag_retrieve(
        self, company_url: str, query: str, hops: int = 2,
    ) -> str:
        """Retrieve context for chat by combining profile data with graph-traversed neighbors."""
        company_id = url_to_id(company_url)

        # 1. Get company profile
        profile_result = await self.db.query(
            f"SELECT * FROM profile:{company_id}"
        )
        profile_text = ""
        if profile_result:
            row = _extract_row(profile_result)
            sections = row.get("sections", {})
            if sections:
                profile_text = f"## Company Profile\n{json.dumps(sections, indent=2, default=str)}\n\n"

        # 2. Get all connected entities (1-hop)
        graph_result = await self.db.query(
            f"SELECT *, "
            f"->works_at->person.* AS people, "
            f"->has_risk->risk.* AS risks, "
            f"->has_certification->certification.* AS certifications, "
            f"->supplies_to->company.* AS suppliers "
            f"FROM company:{company_id}"
        )

        graph_context = ""
        if graph_result:
            row = _extract_row(graph_result)
            people = row.get("people", [])
            risks = row.get("risks", [])
            certs = row.get("certifications", [])
            suppliers = row.get("suppliers", [])

            if people and isinstance(people, list):
                graph_context += "## Key People (from Knowledge Graph)\n"
                for p in people:
                    if isinstance(p, dict):
                        graph_context += f"- {p.get('name', 'Unknown')}: {json.dumps({k: v for k, v in p.items() if k not in ('text_embedding', 'graph_embedding', 'id')}, default=str)}\n"
                graph_context += "\n"

            if risks and isinstance(risks, list):
                graph_context += "## Risks (from Knowledge Graph)\n"
                for r in risks:
                    if isinstance(r, dict):
                        graph_context += f"- [{r.get('severity', 'unknown')}] {r.get('name', '')}: {r.get('description', '')}\n"
                graph_context += "\n"

            if certs and isinstance(certs, list):
                graph_context += "## Certifications (from Knowledge Graph)\n"
                for c in certs:
                    if isinstance(c, dict):
                        graph_context += f"- {c.get('name', '')}\n"
                graph_context += "\n"

            if suppliers and isinstance(suppliers, list):
                graph_context += "## Connected Companies/Suppliers (from Knowledge Graph)\n"
                for s in suppliers:
                    if isinstance(s, dict):
                        graph_context += f"- {s.get('name', s.get('url', 'Unknown'))}"
                        if s.get("risk_score") is not None:
                            graph_context += f" (risk score: {s['risk_score']})"
                        graph_context += "\n"
                graph_context += "\n"

        # 3. Get 2nd-hop supplier risks if hops >= 2
        second_hop = ""
        if hops >= 2:
            hop2_result = await self.db.query(
                f"SELECT ->supplies_to->company->has_risk->risk.* AS supplier_risks, "
                f"->supplies_to->company.name AS supplier_names "
                f"FROM company:{company_id}"
            )
            if hop2_result:
                row = _extract_row(hop2_result)
                s_risks = row.get("supplier_risks", [])
                if s_risks and isinstance(s_risks, list) and len(s_risks) > 0:
                    second_hop += "## Supplier Risks (2nd-degree, from Knowledge Graph)\n"
                    for r in s_risks:
                        if isinstance(r, dict):
                            second_hop += f"- [{r.get('severity', 'unknown')}] {r.get('name', '')}: {r.get('description', '')}\n"
                    second_hop += "\n"

        # 4. Get risk score
        risk_data = await self.compute_risk_score(company_url)
        risk_context = (
            f"## Risk Assessment\n"
            f"Overall Risk Score: {risk_data['risk_score']}\n"
            f"Direct Risks: {risk_data['direct_risk_count']}\n"
            f"Supplier-linked Risks: {risk_data['supplier_risk_count']}\n\n"
        )

        return profile_text + graph_context + second_hop + risk_context

    # ── Graph data for vis-network ──

    async def get_graph_data(self, company_url: str) -> dict[str, Any]:
        """Return nodes and edges in vis-network format for frontend visualization."""
        company_id = url_to_id(company_url)

        graph_result = await self.db.query(
            f"SELECT *, "
            f"->works_at->person.* AS people, "
            f"->has_risk->risk.* AS risks, "
            f"->has_certification->certification.* AS certifications, "
            f"->supplies_to->company.* AS suppliers "
            f"FROM company:{company_id}"
        )

        nodes = []
        edges = []
        seen_ids = set()

        row = _extract_row(graph_result) if graph_result else {}
        company_name = row.get("name", company_url)
        company_node_id = f"company:{company_id}"

        nodes.append({
            "id": company_node_id,
            "label": company_name or company_url,
            "group": "company",
            "title": json.dumps(_sanitize({k: v for k, v in row.items()
                if k not in ("people", "risks", "certifications", "suppliers",
                             "text_embedding", "graph_embedding")}), indent=2, default=str),
        })
        seen_ids.add(company_node_id)

        for p in (row.get("people") or []):
            if not isinstance(p, dict):
                continue
            pid = str(p.get("id", f"person:{name_to_id(p.get('name', 'unknown'))}"))
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            nodes.append({"id": pid, "label": p.get("name", "Unknown"), "group": "person",
                          "title": f"{p.get('role', '')} at {company_name}"})
            edges.append({"from": company_node_id, "to": pid, "label": "works_at"})

        for r in (row.get("risks") or []):
            if not isinstance(r, dict):
                continue
            rid = str(r.get("id", f"risk:{name_to_id(r.get('name', 'unknown'))}"))
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            nodes.append({"id": rid, "label": r.get("name", "Unknown"), "group": "risk",
                          "title": f"[{r.get('severity', 'unknown')}] {r.get('description', '')}"})
            edges.append({"from": company_node_id, "to": rid, "label": "has_risk"})

        for c in (row.get("certifications") or []):
            if not isinstance(c, dict):
                continue
            cid = str(c.get("id", f"cert:{name_to_id(c.get('name', 'unknown'))}"))
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            nodes.append({"id": cid, "label": c.get("name", "Unknown"), "group": "certification",
                          "title": c.get("name", "")})
            edges.append({"from": company_node_id, "to": cid, "label": "has_certification"})

        for s in (row.get("suppliers") or []):
            if not isinstance(s, dict):
                continue
            sid = str(s.get("id", f"company:{name_to_id(s.get('name', 'unknown'))}"))
            if sid in seen_ids:
                continue
            seen_ids.add(sid)
            nodes.append({"id": sid, "label": s.get("name", s.get("url", "Unknown")), "group": "company",
                          "title": f"Risk score: {s.get('risk_score', 'N/A')}"})
            edges.append({"from": company_node_id, "to": sid, "label": "supplies_to"})

        return {"nodes": nodes, "edges": edges}

    # ── Similar companies via graph embeddings ──

    async def find_similar_companies(
        self, company_url: str, top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Find similar companies using cosine similarity on graph embeddings.
        Falls back to text_embedding if graph_embedding is not available."""
        company_id = url_to_id(company_url)

        # Get the target company's embeddings
        target_result = await self.db.query(
            f"SELECT graph_embedding, text_embedding, name, url "
            f"FROM company:{company_id}"
        )
        target_row = _extract_row(target_result)
        target_graph = target_row.get("graph_embedding")
        target_text = target_row.get("text_embedding")

        if not target_graph and not target_text:
            return []

        # Get all other companies' embeddings
        all_result = await self.db.query(
            "SELECT id, graph_embedding, text_embedding, name, url, risk_score, "
            "blacklisted FROM company"
        )
        rows = []
        if all_result and isinstance(all_result, list):
            first = all_result[0]
            if isinstance(first, dict) and "result" in first:
                rows = first["result"]
            elif isinstance(first, dict):
                rows = all_result
            else:
                rows = []

        results = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("id", ""))
            if company_id in row_id:
                continue  # skip self

            # Compare graph embeddings first, fall back to text
            other_graph = row.get("graph_embedding")
            other_text = row.get("text_embedding")

            score = 0.0
            method = ""
            if target_graph and other_graph:
                score = _cosine_similarity(target_graph, other_graph)
                method = "graph_embedding"
            elif target_text and other_text:
                score = _cosine_similarity(target_text, other_text)
                method = "text_embedding"
            else:
                continue

            results.append({
                "company_id": row_id,
                "name": row.get("name"),
                "url": row.get("url"),
                "similarity": round(score, 4),
                "method": method,
                "risk_score": row.get("risk_score"),
                "blacklisted": row.get("blacklisted", False),
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    # ── Blacklist check ──

    async def mark_blacklisted(self, company_url: str) -> None:
        """Mark a company as blacklisted in the graph."""
        company_id = url_to_id(company_url)
        await self.db.merge(f"company:{company_id}", {"blacklisted": True})
        logger.info("Marked %s as blacklisted", company_url)

    async def blacklist_check(
        self, company_url: str, threshold: float | None = None,
    ) -> dict[str, Any]:
        """Check if a company is similar to any blacklisted company.
        Returns matches above threshold with similarity scores."""
        if threshold is None:
            threshold = BLACKLIST_SIMILARITY_THRESHOLD

        similar = await self.find_similar_companies(company_url, top_k=20)

        matches = [
            s for s in similar
            if s.get("blacklisted") and s["similarity"] >= threshold
        ]

        flagged = len(matches) > 0
        max_sim = max((m["similarity"] for m in matches), default=0.0)

        return {
            "company_url": company_url,
            "flagged": flagged,
            "threshold": threshold,
            "highest_similarity": round(max_sim, 4),
            "blacklist_matches": matches,
            "all_similar": similar[:5],
        }


BLACKLIST_SIMILARITY_THRESHOLD = 0.75


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _sanitize(obj: Any) -> Any:
    """Convert SurrealDB types (RecordID, etc.) to JSON-serializable types."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items() if k != "text_embedding" and k != "graph_embedding"}
    if isinstance(obj, list):
        return [_sanitize(item) for item in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


def _extract_row(result: list) -> dict:
    """Extract the first data row from SurrealDB query result."""
    if not result:
        return {}
    first = result[0]
    if isinstance(first, dict):
        if "result" in first:
            rows = first["result"]
            return rows[0] if rows else {}
        return first
    return {}


def _entity_type_to_relation(etype: str) -> str | None:
    mapping = {
        "person": "works_at",
        "risk": "has_risk",
        "certification": "has_certification",
        "company": "supplies_to",
    }
    return mapping.get(etype)
