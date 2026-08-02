"""
Hotspot network builder.

Pipeline:
  1. Load candidate papers from the database
  2. Build paper text embeddings with FastEmbed (cached in paper_features)
  3. Build a mutual kNN semantic graph
  4. Add topic / reference Jaccard edges → weighted hybrid graph
  5. Leiden community detection → topic clusters
  6. Match clusters with historical topics via the Hungarian algorithm
  7. Score topic "hotness" from recent vs baseline share shifts
  8. Reduce paper embeddings to 2-D with UMAP (fixed coords for the map)
  9. Generate Chinese labels via the Anthropic-compatible LLM
  10. Write validated static JSON to frontend/public/data/hotspots/
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import Config
from .storage import PaperFeatures, PaperStorage
from .hotspot_labels import TopicLabeler


# ── helpers ──────────────────────────────────────────────────────────

def _ndarray_to_blob(arr: np.ndarray) -> bytes:
    return arr.astype(np.float32).tobytes()


def _blob_to_ndarray(blob: bytes, dim: int) -> np.ndarray:
    arr = np.frombuffer(blob, dtype=np.float32)
    if arr.size != dim:
        raise ValueError(f"Embedding dimension mismatch: expected {dim}, got {arr.size}")
    return arr.copy()


def _ensure_output_dirs(public_data_dir: Path) -> Tuple[Path, Path]:
    """Return (temp_dir, final_dir) for atomic output replacement."""
    final_dir = public_data_dir / "hotspots"
    temp_dir = public_data_dir / ".hotspots-next"
    temp_dir.mkdir(parents=True, exist_ok=True)
    final_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir, final_dir


def _atomic_replace(temp_dir: Path, final_dir: Path) -> None:
    """Replace final_dir contents with temp_dir contents atomically."""
    # Remove old final dir contents
    for path in final_dir.iterdir():
        if path.is_dir():
            _rmtree(path)
        else:
            path.unlink()
    # Move temp contents into final
    for path in temp_dir.iterdir():
        os.replace(str(path), str(final_dir / path.name))
    temp_dir.rmdir()


def _rmtree(dir_path: Path) -> None:
    for entry in dir_path.iterdir():
        if entry.is_dir():
            _rmtree(entry)
        else:
            entry.unlink()
    dir_path.rmdir()


# ── step 1: load candidates ──────────────────────────────────────────

class NoHotspotCandidatesError(ValueError):
    """Raised when there are no screened papers to analyze.

    This is a graceful-skip condition (e.g. a first run against an empty
    database), not a build failure. The CLI treats it as a no-op.
    """


def _load_candidates(
    storage: PaperStorage,
    analysis_days: int,
    min_date: str,
) -> List[Dict[str, Any]]:
    """Load screened High/Medium papers within the analysis window."""
    candidates = storage.get_analysis_candidates(
        min_date=min_date,
        relevance_filter=("High", "Medium"),
    )
    if not candidates:
        raise NoHotspotCandidatesError(
            f"No screened High/Medium papers found since {min_date}. "
            "Run screen-pending first."
        )
    return candidates


# ── step 2: embeddings ───────────────────────────────────────────────

def _paper_text(paper: Dict[str, Any]) -> str:
    """Build the text that feeds the embedding model."""
    parts: List[str] = []
    title = str(paper.get("title") or "").strip()
    if title:
        parts.append(f"Title: {title}")

    abstract = str(paper.get("abstract") or paper.get("summary") or "").strip()
    if abstract:
        parts.append(f"Abstract: {abstract}")

    # Include OpenAlex topic names when available
    topics = _parse_json_field(paper.get("openalex_topics_json"))
    topic_names = [t.get("name", "") for t in topics if t.get("name")]
    if topic_names:
        parts.append(f"Topics: {', '.join(topic_names[:8])}")

    keywords = _parse_json_field(paper.get("openalex_keywords_json"))
    kw_names = [k.get("name", "") for k in keywords if k.get("name")]
    if kw_names:
        parts.append(f"Keywords: {', '.join(kw_names[:8])}")

    return "\n".join(parts).strip()


def _parse_json_field(value: Any) -> Any:
    """Parse a JSON string field, returning the parsed value or a default."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            pass
    return []


def _compute_embeddings(
    candidates: List[Dict[str, Any]],
    storage: PaperStorage,
    embedding_model: str,
    cache_dir: str,
) -> np.ndarray:
    """Compute or load cached embeddings for candidate papers.

    Returns a (N, D) float32 array in the same order as `candidates`.
    """
    from fastembed import TextEmbedding

    model = TextEmbedding(
        model_name=embedding_model,
        cache_dir=cache_dir,
    )

    texts: List[str] = []
    paper_ids: List[int] = []
    needs_embedding: List[int] = []  # indices into texts/paper_ids

    for idx, paper in enumerate(candidates):
        pid = int(paper["id"])
        text = _paper_text(paper)
        if not text:
            continue

        text_hash = storage.compute_text_hash(
            str(paper.get("title") or ""),
            str(paper.get("abstract") or paper.get("summary") or ""),
            embedding_model,
        )

        # Reuse cached embedding if the text hasn't changed
        existing = storage.get_paper_features(pid)
        if (
            existing
            and existing.embedding_bytes
            and existing.text_hash == text_hash
            and existing.embedding_model == embedding_model
        ):
            continue  # already cached, will be loaded below

        texts.append(text)
        paper_ids.append(pid)
        needs_embedding.append(idx)

    # Compute new embeddings in batches
    if texts:
        batch_size = 64
        all_vectors: List[np.ndarray] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            vectors = list(model.embed(batch))
            all_vectors.extend(vectors)
            if i + batch_size < len(texts):
                time.sleep(0.05)

        dim = int(all_vectors[0].shape[0]) if all_vectors else 384

        for j, (pid, vec) in enumerate(zip(paper_ids, all_vectors)):
            blob = _ndarray_to_blob(np.asarray(vec, dtype=np.float32))
            text_hash = storage.compute_text_hash(
                str(candidates[needs_embedding[j]].get("title") or ""),
                str(candidates[needs_embedding[j]].get("abstract") or candidates[needs_embedding[j]].get("summary") or ""),
                embedding_model,
            )
            features = PaperFeatures(
                paper_id=pid,
                text_hash=text_hash,
                embedding_model=embedding_model,
                embedding_dim=dim,
                embedding_bytes=blob,
            )
            storage.upsert_paper_features(features)

    # Now load all embeddings (from cache or freshly stored)
    embeddings: List[np.ndarray] = []
    valid_indices: List[int] = []
    for idx, paper in enumerate(candidates):
        pf = storage.get_paper_features(int(paper["id"]))
        if pf and pf.embedding_bytes and pf.embedding_dim > 0:
            try:
                emb = _blob_to_ndarray(pf.embedding_bytes, pf.embedding_dim)
                embeddings.append(emb)
                valid_indices.append(idx)
            except (ValueError, TypeError):
                continue

    if len(embeddings) < 10:
        raise ValueError(
            f"Only {len(embeddings)} papers have valid embeddings; need at least 10."
        )

    # Trim candidates to those with valid embeddings
    candidates[:] = [candidates[i] for i in valid_indices]

    return np.stack(embeddings, axis=0).astype(np.float32)


# ── step 2b: UMAP 2-D reduction + per-paper recency heat ─────────────

def _compute_umap(
    embeddings: np.ndarray,
    n_neighbors: int = 15,
    min_dist: float = 0.1,
    random_state: int = 42,
) -> np.ndarray:
    """Reduce paper embeddings to normalized 2-D coordinates with UMAP.

    Returns an (N, 2) float array normalized to roughly [-1, 1]. The random
    state is fixed so identical inputs produce identical maps across runs.
    """
    import umap

    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric="cosine",
        random_state=random_state,
        verbose=False,
    )
    coords = reducer.fit_transform(embeddings).astype(np.float64)
    max_abs = np.max(np.abs(coords)) or 1.0
    return (coords / max_abs).round(4)


def _paper_recency_heat(
    candidates: List[Dict[str, Any]],
    anchor_date: date,
    half_life_days: float = 45.0,
) -> List[float]:
    """Per-paper 0-100 recency heat (exponential decay from anchor date).

    Used as the particle-dot size so recent papers read brighter in the map.
    Papers without a parseable date get a middle value.
    """
    heats: List[float] = []
    for cand in candidates:
        raw = str(cand.get("published_date") or "")
        try:
            pub = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            heats.append(50.0)
            continue
        days = max(0.0, (anchor_date - pub).days)
        score = math.exp(-days / half_life_days) * 100.0
        heats.append(round(score, 1))
    return heats


# ── step 3: mutual kNN graph ─────────────────────────────────────────

def _build_mutual_knn(
    embeddings: np.ndarray,
    k: int,
    min_similarity: float,
) -> List[Tuple[int, int, float]]:
    """Build mutual k-NN edges with cosine similarity."""
    from sklearn.neighbors import NearestNeighbors

    n = embeddings.shape[0]
    effective_k = min(k + 1, n)  # +1 because self is included

    nn = NearestNeighbors(
        n_neighbors=effective_k,
        metric="cosine",
        algorithm="brute",
        n_jobs=-1,
    )
    nn.fit(embeddings)
    distances, indices = nn.kneighbors(embeddings)

    edges: Dict[Tuple[int, int], float] = {}
    for i in range(n):
        for j_idx in range(1, effective_k):  # skip self at position 0
            j = int(indices[i][j_idx])
            sim = float(1.0 - distances[i][j_idx])
            if sim < min_similarity:
                continue
            # Check mutual: j also has i in its neighborhood
            j_neighbors = set(int(x) for x in indices[j][1:effective_k])
            if i in j_neighbors:
                key = (min(i, j), max(i, j))
                if key not in edges or sim > edges[key]:
                    edges[key] = sim

    return [(i, j, s) for (i, j), s in edges.items()]


# ── step 4: hybrid edge weights ──────────────────────────────────────

def _topic_jaccard(topics_i: List[Dict], topics_j: List[Dict]) -> float:
    ids_i = {t.get("id", t.get("name", "")) for t in topics_i}
    ids_j = {t.get("id", t.get("name", "")) for t in topics_j}
    if not ids_i or not ids_j:
        return 0.0
    intersection = ids_i & ids_j
    union = ids_i | ids_j
    return len(intersection) / len(union) if union else 0.0


def _reference_jaccard(refs_i: List[str], refs_j: List[str]) -> float:
    set_i = set(refs_i)
    set_j = set(refs_j)
    if not set_i or not set_j:
        return 0.0
    return len(set_i & set_j) / len(set_i | set_j)


def _compute_hybrid_edges(
    knn_edges: List[Tuple[int, int, float]],
    candidates: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> List[Tuple[int, int, float]]:
    """Augment semantic edges with topic and reference Jaccard."""
    w_sem = float(config.get("semantic_weight", 0.70))
    w_topic = float(config.get("topic_weight", 0.20))
    w_ref = float(config.get("reference_weight", 0.10))
    min_weight = float(config.get("minimum_edge_weight", 0.45))

    # Pre-parse metadata
    topics_cache: Dict[int, List[Dict]] = {}
    refs_cache: Dict[int, List[str]] = {}
    for idx, paper in enumerate(candidates):
        topics_cache[idx] = _parse_json_field(paper.get("openalex_topics_json"))
        refs_cache[idx] = _parse_json_field(paper.get("referenced_works_json"))

    hybrid: List[Tuple[int, int, float]] = []
    for i, j, sem_sim in knn_edges:
        topic_sim = _topic_jaccard(topics_cache.get(i, []), topics_cache.get(j, []))
        ref_sim = _reference_jaccard(refs_cache.get(i, []), refs_cache.get(j, []))

        # Renormalize weights if references are missing
        has_ref = bool(refs_cache.get(i) and refs_cache.get(j))
        if has_ref:
            total = w_sem + w_topic + w_ref
            weight = (w_sem * sem_sim + w_topic * topic_sim + w_ref * ref_sim) / total
        else:
            total = w_sem + w_topic
            weight = (w_sem * sem_sim + w_topic * topic_sim) / total if total > 0 else sem_sim

        if weight >= min_weight:
            hybrid.append((i, j, weight))

    # Limit to 8 edges per node
    node_edges: Dict[int, List[Tuple[int, int, float]]] = {}
    for i, j, w in hybrid:
        node_edges.setdefault(i, []).append((i, j, w))
        node_edges.setdefault(j, []).append((i, j, w))

    limited: set = set()
    for node, edges in node_edges.items():
        edges.sort(key=lambda x: x[2], reverse=True)
        for e in edges[:8]:
            limited.add((min(e[0], e[1]), max(e[0], e[1])))

    # Deduplicate by (min, max) key, keeping the highest weight
    deduped: Dict[Tuple[int, int], float] = {}
    for i, j, w in hybrid:
        key = (min(i, j), max(i, j))
        if key in limited and w > deduped.get(key, -1.0):
            deduped[key] = w
    return [(i, j, w) for (i, j), w in deduped.items()]


# ── step 5: Leiden clustering ────────────────────────────────────────

def _leiden_clusters(
    n_papers: int,
    edges: List[Tuple[int, int, float]],
    resolution: float,
    iterations: int,
    seed: int = 42,
) -> Dict[int, int]:
    """Run Leiden community detection. Returns {paper_idx: cluster_id}."""
    import random

    import igraph as ig

    if not edges:
        # Every paper is its own cluster
        return {i: i for i in range(n_papers)}

    edge_list = [(i, j) for i, j, _ in edges]
    weights = [w for _, _, w in edges]

    g = ig.Graph(n=n_papers, edges=edge_list, directed=False)
    g.es["weight"] = weights

    # igraph's Leiden uses a global RNG; seed it for reproducibility.
    ig.set_random_number_generator(random.Random(seed))
    partition = g.community_leiden(
        objective_function="modularity",
        weights="weight",
        resolution=resolution,
        n_iterations=iterations,
    )

    membership: Dict[int, int] = {}
    for cluster_id, members in enumerate(partition):
        for node in members:
            membership[node] = cluster_id
    return membership


# ── step 6: form topics from clusters ────────────────────────────────

def _form_topics(
    membership: Dict[int, int],
    candidates: List[Dict[str, Any]],
    embeddings: np.ndarray,
    min_cluster_size: int,
) -> List[Dict[str, Any]]:
    """Group clusters into topic dicts; label small ones as noise."""
    clusters: Dict[int, List[int]] = {}
    for paper_idx, cluster_id in membership.items():
        clusters.setdefault(cluster_id, []).append(paper_idx)

    topics: List[Dict[str, Any]] = []
    noise_indices: List[int] = []
    for cluster_id, members in clusters.items():
        if len(members) >= min_cluster_size:
            centroid = embeddings[members].mean(axis=0)
            topics.append({
                "cluster_id": cluster_id,
                "paper_indices": members,
                "size": len(members),
                "centroid": centroid,
                "status": "formal",
            })
        elif len(members) >= 2:
            # Small cluster: candidate emerging topic
            centroid = embeddings[members].mean(axis=0)
            topics.append({
                "cluster_id": cluster_id,
                "paper_indices": members,
                "size": len(members),
                "centroid": centroid,
                "status": "emerging",
            })

    return topics


# ── step 7: match with historical topics ─────────────────────────────

def _load_previous_topics(final_dir: Path) -> List[Dict[str, Any]]:
    """Load previous run's graph.json for topic lineage matching."""
    graph_path = final_dir / "graph.json"
    if not graph_path.exists():
        return []
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        return data.get("topics_meta", [])
    except (json.JSONDecodeError, KeyError):
        return []


def _match_topics(
    current: List[Dict[str, Any]],
    previous: List[Dict[str, Any]],
    embeddings: np.ndarray,
    candidates: List[Dict[str, Any]],
    match_threshold: float,
    drift_threshold: float,
) -> List[Dict[str, Any]]:
    """Match current topics to previous using Hungarian algorithm.

    Each topic gets a stable topic_id and lineage_status.
    """
    if not previous:
        for topic in current:
            topic["topic_id"] = f"topic_{uuid.uuid4().hex[:8]}"
            topic["lineage_status"] = "new"
        return current

    from scipy.optimize import linear_sum_assignment

    n_curr = len(current)
    n_prev = len(previous)

    # Build cost matrix (1 - match_score)
    cost = np.ones((max(n_curr, n_prev), max(n_curr, n_prev)), dtype=np.float64)

    for i, ct in enumerate(current):
        for j, pt in enumerate(previous):
            # Centroid cosine similarity
            c_emb = np.asarray(ct["centroid"], dtype=np.float64)
            p_emb = np.asarray(pt.get("centroid", []), dtype=np.float64)
            if p_emb.size == 0 or c_emb.size == 0:
                cos_sim = 0.0
            else:
                dot = np.dot(c_emb, p_emb)
                norm = np.linalg.norm(c_emb) * np.linalg.norm(p_emb)
                cos_sim = float(dot / norm) if norm > 0 else 0.0

            # Paper ID Jaccard
            curr_ids = set(
                candidates[idx]["id"] for idx in ct["paper_indices"]
            )
            prev_ids = set(pt.get("paper_ids", []))
            jaccard = (
                len(curr_ids & prev_ids) / len(curr_ids | prev_ids)
                if curr_ids | prev_ids
                else 0.0
            )

            match_score = 0.75 * cos_sim + 0.25 * jaccard
            cost[i, j] = 1.0 - match_score

    row_ind, col_ind = linear_sum_assignment(cost)

    matched_prev: set = set()
    for i, j in zip(row_ind, col_ind):
        if i >= n_curr:
            continue
        match_score = 1.0 - cost[i, j]

        if j < n_prev and match_score >= match_threshold:
            current[i]["topic_id"] = previous[j].get("topic_id", f"topic_{uuid.uuid4().hex[:8]}")
            current[i]["previous_topic_id"] = current[i]["topic_id"]
            current[i]["lineage_status"] = "continued"
            matched_prev.add(j)
        elif j < n_prev and match_score >= drift_threshold:
            current[i]["topic_id"] = previous[j].get("topic_id", f"topic_{uuid.uuid4().hex[:8]}")
            current[i]["previous_topic_id"] = current[i]["topic_id"]
            current[i]["lineage_status"] = "drifted"
            matched_prev.add(j)
        else:
            current[i]["topic_id"] = f"topic_{uuid.uuid4().hex[:8]}"
            current[i]["lineage_status"] = "new"

    return current


# ── step 8: heat scoring ─────────────────────────────────────────────

def _compute_heat_scores(
    topics: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    recent_days: int,
    baseline_days: int,
    anchor_date: date,
    min_recent_for_hot: int,
) -> List[Dict[str, Any]]:
    """Score each topic by recent vs baseline share shift."""
    recent_start = anchor_date - timedelta(days=recent_days)
    baseline_start = anchor_date - timedelta(days=recent_days + baseline_days)
    baseline_end = anchor_date - timedelta(days=recent_days)

    total_recent = 0
    total_baseline = 0

    for paper in candidates:
        pub_str = str(paper.get("published_date", "") or "")
        try:
            pub_date = datetime.strptime(pub_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if recent_start <= pub_date <= anchor_date:
            total_recent += 1
        if baseline_start <= pub_date <= baseline_end:
            total_baseline += 1

    # Pass 1: compute per-topic metrics for every topic
    for topic in topics:
        recent_count = 0
        baseline_count = 0
        paper_ids: List[int] = []
        journal_names: set = set()

        for idx in topic["paper_indices"]:
            paper = candidates[idx]
            paper_ids.append(int(paper["id"]))
            journal = str(paper.get("journal") or "").strip()
            if journal:
                journal_names.add(journal)

            pub_str = str(paper.get("published_date", "") or "")
            try:
                pub_date = datetime.strptime(pub_str[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            if recent_start <= pub_date <= anchor_date:
                recent_count += 1
            if baseline_start <= pub_date <= baseline_end:
                baseline_count += 1

        topic["paper_ids"] = paper_ids
        topic["recent_count"] = recent_count
        topic["baseline_count"] = baseline_count
        topic["journal_count"] = len(journal_names)

    max_recent_count = max((t["recent_count"] for t in topics), default=0)

    # Pass 2: compute derived scores using all topics' metrics
    for topic in topics:
        recent_count = topic["recent_count"]
        baseline_count = topic["baseline_count"]

        # Growth score (smoothed log ratio)
        recent_share = (recent_count + 0.5) / (total_recent + 1) if total_recent > 0 else 0
        baseline_share = (baseline_count + 0.5) / (total_baseline + 1) if total_baseline > 0 else 0
        growth_raw = math.log((recent_share + 0.005) / (baseline_share + 0.005))
        growth_score = 1.0 / (1.0 + math.exp(-3.0 * growth_raw))  # sigmoid squash

        # Volume score (percentile among all topics)
        volume_score = min(1.0, recent_count / max(1, max_recent_count))

        # Spread score (normalized journal entropy)
        if topic["journal_count"] > 1:
            spread_score = min(1.0, math.log(topic["journal_count"]) / math.log(4))
        else:
            spread_score = 0.0

        # Recency score (exponential decay with 14-day half-life)
        recency_sum = 0.0
        for idx in topic["paper_indices"]:
            pub_str = str(candidates[idx].get("published_date", "") or "")
            try:
                pub_date = datetime.strptime(pub_str[:10], "%Y-%m-%d").date()
                age_days = (anchor_date - pub_date).days
                recency_sum += math.exp(-0.0495 * max(0, age_days))  # ln(2)/14 ≈ 0.0495
            except (ValueError, TypeError):
                pass
        recency_score = min(1.0, recency_sum / max(1, topic["size"]))

        # Quality score (internal edge density proxy — cluster size coherence)
        quality_score = min(1.0, topic["size"] / 10.0)

        hot_score = (
            0.40 * growth_score
            + 0.25 * volume_score
            + 0.15 * spread_score
            + 0.10 * recency_score
            + 0.10 * quality_score
        )

        topic["hot_score"] = round(float(hot_score), 4)
        topic["growth"] = round(float(growth_score), 4)
        topic["display_score"] = round(float(hot_score) * 100)

        # Mark as hot if meets threshold
        topic["is_hot"] = bool(
            recent_count >= min_recent_for_hot
            or (recent_count >= 2 and growth_score >= 0.7)
        )

    return topics


# ── step 9: layout ───────────────────────────────────────────────────

def _compute_topic_graph(
    topics: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
    paper_edges: List[Tuple[int, int, float]],
) -> List[Tuple[int, int, float]]:
    """Build the topic-level graph from the paper-level edge set.

    Only paper pairs that already have a real (hybrid) edge contribute to a
    topic connection, so unrelated topics never get spuriously linked. Each
    cross-topic paper edge increments the topic-pair count; the final weight
    is normalized by the geometric mean of the two topic sizes.
    """
    paper_to_topic: Dict[int, int] = {}
    for topic in topics:
        for p_idx in topic["paper_indices"]:
            paper_to_topic[p_idx] = topic["cluster_id"]

    topic_edges: Dict[Tuple[int, int], float] = {}
    for i, j, _w in paper_edges:
        ti = paper_to_topic.get(i)
        tj = paper_to_topic.get(j)
        if ti is None or tj is None or ti == tj:
            continue
        key = (min(ti, tj), max(ti, tj))
        topic_edges[key] = topic_edges.get(key, 0.0) + 1.0

    # Normalize by sqrt of topic sizes
    topic_sizes = {t["cluster_id"]: t["size"] for t in topics}
    normalized: List[Tuple[int, int, float]] = []
    for (ti, tj), raw in topic_edges.items():
        norm = math.sqrt(topic_sizes.get(ti, 1) * topic_sizes.get(tj, 1))
        weight = raw / norm if norm > 0 else 0
        normalized.append((ti, tj, float(weight)))

    return normalized


def _compute_anchor_positions(
    topics: List[Dict[str, Any]],
    umap_coords: np.ndarray,
) -> Dict[int, Tuple[float, float]]:
    """Topic-cloud anchor positions = centroid of member papers' UMAP coords.

    Each UMAP run is fit independently, so the coordinate space is NOT stable
    across weekly updates. Blending in the previous run's anchor coordinates
    would pull anchors away from the actual point cloud — anchors must be the
    pure centroid of the current run's member papers.
    """
    result: Dict[int, Tuple[float, float]] = {}
    for topic in topics:
        members = topic.get("paper_indices", [])
        if members:
            cx = float(np.mean(umap_coords[members, 0]))
            cy = float(np.mean(umap_coords[members, 1]))
        else:
            cx, cy = 0.0, 0.0
        result[topic["cluster_id"]] = (round(cx, 4), round(cy, 4))
    return result


# ── step 10: output JSON ─────────────────────────────────────────────

def _build_output(
    topics: List[Dict[str, Any]],
    topic_edges: List[Tuple[int, int, float]],
    anchor_positions: Dict[int, Tuple[float, float]],
    umap_coords: np.ndarray,
    paper_heat: List[float],
    candidates: List[Dict[str, Any]],
    config: Dict[str, Any],
    anchor_date: date,
    embedding_model: str,
    embedding_dim: int,
    umap_config: Dict[str, Any],
    temp_dir: Path,
) -> Path:
    """Write graph.json (semantic map), trends.json, manifest.json, topics/.

    graph.json now holds a paper-level semantic map: every analysis paper is
    a small point positioned by its UMAP coordinate, colored by topic group;
    one topic anchor point per cloud sits at the member centroid and carries
    the display label. Topic-relation links connect cloud anchors.
    """
    max_topics = int(config.get("max_topics", 40))

    # Sort by hot_score descending, keep top N
    sorted_topics = sorted(topics, key=lambda t: t.get("hot_score", 0), reverse=True)
    displayed = sorted_topics[:max_topics]

    # topic index = position in `displayed` (stable color / cluster group)
    cid_to_idx = {t["cluster_id"]: i for i, t in enumerate(displayed)}

    # Map candidate index -> its displayed topic (None = noise paper)
    cand_to_topic: List[Optional[Dict[str, Any]]] = [None] * len(candidates)
    for t in displayed:
        for p_idx in t["paper_indices"]:
            cand_to_topic[p_idx] = t

    points: List[Dict[str, Any]] = []
    topic_meta: List[Dict[str, Any]] = []

    # Paper points — every analysis paper, positioned by UMAP.
    for i, cand in enumerate(candidates):
        topic = cand_to_topic[i]
        points.append({
            "id": f"p_{cand['id']}",
            "type": "paper",
            "shape": 0,
            "paperId": int(cand["id"]),
            "title": str(cand.get("title") or ""),
            "topic": cid_to_idx[topic["cluster_id"]] if topic else -1,
            "topicId": topic["topic_id"] if topic else "noise",
            "label": "",
            "heat": round(paper_heat[i], 1),
            "x": round(float(umap_coords[i, 0]), 4),
            "y": round(float(umap_coords[i, 1]), 4),
        })

    # Topic anchor points — one per cloud at the centroid, only these label.
    for i, t in enumerate(displayed):
        cid = t["cluster_id"]
        x, y = anchor_positions.get(cid, (0.0, 0.0))
        topic_slug = t["topic_id"]
        points.append({
            "id": topic_slug,
            "type": "topic",
            "shape": 6,
            "topicId": topic_slug,
            "topic": i,
            "label": t.get("label_zh") or t.get("label_en", topic_slug),
            "heat": t["display_score"],
            "paperCount": t["size"],
            "journalCount": t["journal_count"],
            "growth": round(t.get("growth", 0), 3),
            "status": t.get("lineage_status", "new"),
            "detailFile": f"topics/{topic_slug}.json",
            "x": x,
            "y": y,
        })
        topic_meta.append({
            "topic_id": topic_slug,
            "cluster_id": cid,
            "size": t["size"],
            "hot_score": t["hot_score"],
            "centroid": t["centroid"].tolist() if hasattr(t["centroid"], "tolist") else list(t["centroid"]),
            "paper_ids": t.get("paper_ids", []),
            "x": x,
            "y": y,
        })

    # Topic-relation links (cluster_id -> topic_id, both in displayed)
    cid_to_slug = {t["cluster_id"]: t["topic_id"] for t in displayed}
    edges_out: List[Dict[str, Any]] = []
    for ti, tj, weight in topic_edges:
        si = cid_to_slug.get(ti)
        sj = cid_to_slug.get(tj)
        if not si or not sj:
            continue
        edge_id = f"{si}__{sj}"
        # Avoid duplicates
        if any(e["id"] == edge_id for e in edges_out):
            continue
        edges_out.append({
            "id": edge_id,
            "source": si,
            "target": sj,
            "weight": round(float(weight), 4),
            "width": round(max(0.5, float(weight) * 4.0), 2),
            "opacity": round(min(0.9, max(0.15, float(weight))), 2),
        })

    # Write graph.json
    graph_data = {
        "schema_version": 2,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_model": embedding_model,
        "embedding_dimension": embedding_dim,
        "umap": {
            "n_neighbors": int(umap_config.get("n_neighbors", 15)),
            "min_dist": float(umap_config.get("min_dist", 0.1)),
            "random_state": int(umap_config.get("random_state", 42)),
        },
        "points": points,
        "links": edges_out,
        "topics_meta": topic_meta,
    }
    (temp_dir / "graph.json").write_text(
        json.dumps(graph_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Write trends.json
    trends = []
    for t in displayed:
        trends.append({
            "topic_id": t["topic_id"],
            "label": t.get("label_zh") or t.get("label_en", t["topic_id"]),
            "hot_score": t["display_score"],
            "growth": round(t.get("growth", 0), 3),
            "recent_count": t["recent_count"],
            "baseline_count": t["baseline_count"],
            "journal_count": t["journal_count"],
            "lineage_status": t.get("lineage_status", "new"),
            "is_hot": t.get("is_hot", False),
        })
    (temp_dir / "trends.json").write_text(
        json.dumps(trends, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Write manifest.json
    manifest = {
        "schema_version": 2,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "embedding_model": embedding_model,
        "embedding_dimension": embedding_dim,
        "period": {
            "recent_start": (anchor_date - timedelta(days=int(config.get("recent_days", 30)))).isoformat(),
            "recent_end": anchor_date.isoformat(),
            "baseline_start": (anchor_date - timedelta(days=int(config.get("recent_days", 30)) + int(config.get("baseline_days", 150)))).isoformat(),
            "baseline_end": (anchor_date - timedelta(days=int(config.get("recent_days", 30)))).isoformat(),
        },
        "paper_count": len(candidates),
        "topic_count": len(displayed),
        "edge_count": len(edges_out),
    }
    (temp_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Write per-topic detail files
    topics_dir = temp_dir / "topics"
    topics_dir.mkdir(parents=True, exist_ok=True)
    for t in displayed:
        cid = t["cluster_id"]
        detail = {
            "topic_id": t["topic_id"],
            "label": t.get("label_zh") or t.get("label_en", t["topic_id"]),
            "description": t.get("description", ""),
            "why_hot": t.get("why_hot", ""),
            "hot_score": t["display_score"],
            "growth": round(t.get("growth", 0), 3),
            "recent_count": t["recent_count"],
            "baseline_count": t["baseline_count"],
            "journal_count": t["journal_count"],
            "lineage_status": t.get("lineage_status", "new"),
            "keywords": t.get("keywords", []),
            "papers": [],
            "paper_edges": [],
        }

        # Include paper details
        for idx in t["paper_indices"]:
            paper = candidates[idx]
            detail["papers"].append({
                "id": int(paper["id"]),
                "title": str(paper.get("title") or ""),
                "journal": str(paper.get("journal") or ""),
                "published_date": str(paper.get("published_date") or ""),
                "summary": str(paper.get("summary") or "")[:200],
            })

        (topics_dir / f"{t['topic_id']}.json").write_text(
            json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return temp_dir


# ── public entry point ───────────────────────────────────────────────

def build_hotspot_network(
    config: Config,
    analysis_days: int = 0,
    recent_days: int = 0,
    baseline_days: int = 0,
    max_topics: int = 0,
) -> Path:
    """Run the full hotspot network pipeline and write static JSON.

    Returns the path to the final output directory.
    """
    net_config = config.hotspot_network_config

    analysis_days = analysis_days or int(net_config.get("analysis_days", 180))
    recent_days = recent_days or int(net_config.get("recent_days", 30))
    baseline_days = baseline_days or int(net_config.get("baseline_days", 150))
    embedding_model = str(net_config.get("embedding_model", "BAAI/bge-small-en-v1.5"))
    knn_k = int(net_config.get("knn_k", 8))
    min_sem_sim = float(net_config.get("minimum_semantic_similarity", 0.42))
    leiden_resolution = float(net_config.get("leiden_resolution", 0.8))
    leiden_iterations = int(net_config.get("leiden_iterations", 4))
    match_threshold = float(net_config.get("topic_match_threshold", 0.72))
    drift_threshold = float(net_config.get("topic_drift_threshold", 0.55))
    min_recent = int(net_config.get("min_recent_papers_for_hot", 3))
    min_total = int(net_config.get("min_total_papers_for_topic", 4))
    umap_n_neighbors = int(net_config.get("umap_n_neighbors", 15))
    umap_min_dist = float(net_config.get("umap_min_dist", 0.1))
    umap_seed = int(net_config.get("umap_seed", 42))
    umap_config = {
        "n_neighbors": umap_n_neighbors,
        "min_dist": umap_min_dist,
        "random_state": umap_seed,
    }
    if max_topics > 0:
        net_config = {**net_config, "max_topics": max_topics}

    anchor_date = date.today()
    min_date = (anchor_date - timedelta(days=analysis_days)).isoformat()
    cache_dir = str(config.project_root / ".cache" / "fastembed")

    storage = PaperStorage(config.database_path)

    print("Hotspot network pipeline")
    print("=" * 50)

    # 1. Load candidates — output dirs are only created once we know there is
    #    data to write, so a graceful no-candidates skip leaves nothing behind.
    print(f"[1/9] Loading candidates (since {min_date})...")
    candidates = _load_candidates(storage, analysis_days, min_date)
    print(f"       {len(candidates)} papers loaded")
    temp_dir, final_dir = _ensure_output_dirs(config.public_data_dir)

    # 2. Compute embeddings
    print(f"[2/9] Computing embeddings ({embedding_model})...")
    embeddings = _compute_embeddings(candidates, storage, embedding_model, cache_dir)
    dim = int(embeddings.shape[1])
    print(f"       {embeddings.shape[0]} papers × {dim} dimensions")

    # 2b. UMAP 2-D coords + per-paper recency heat for the semantic map
    print(f"[2b] Reducing to 2-D with UMAP (n_neighbors={umap_n_neighbors}, min_dist={umap_min_dist})...")
    umap_coords = _compute_umap(embeddings, umap_n_neighbors, umap_min_dist, umap_seed)
    paper_heat = _paper_recency_heat(candidates, anchor_date)

    # 3. Build mutual kNN
    print(f"[3/9] Building mutual k-NN graph (k={knn_k}, min_sim={min_sem_sim})...")
    knn_edges = _build_mutual_knn(embeddings, knn_k, min_sem_sim)
    print(f"       {len(knn_edges)} mutual edges")

    # 4. Hybrid edge weights
    print("[4/9] Computing hybrid edge weights...")
    hybrid_edges = _compute_hybrid_edges(knn_edges, candidates, net_config)
    print(f"       {len(hybrid_edges)} edges after filtering")

    # 5. Leiden clustering
    print(f"[5/9] Leiden clustering (resolution={leiden_resolution})...")
    membership = _leiden_clusters(
        len(candidates), hybrid_edges, leiden_resolution, leiden_iterations,
    )
    n_clusters = len(set(membership.values()))
    print(f"       {n_clusters} clusters")

    # 6. Form topics
    print(f"[6/9] Forming topics (min_size={min_total})...")
    topics = _form_topics(membership, candidates, embeddings, min_total)
    print(f"       {len(topics)} topics ({sum(1 for t in topics if t['status'] == 'formal')} formal)")

    if not topics:
        raise ValueError("No valid topics found. Check min_total_papers_for_topic threshold.")

    # 7. Match historical topics
    print("[7/9] Matching historical topics...")
    previous = _load_previous_topics(final_dir)
    topics = _match_topics(
        topics, previous, embeddings, candidates, match_threshold, drift_threshold,
    )
    continued = sum(1 for t in topics if t.get("lineage_status") == "continued")
    new_count = sum(1 for t in topics if t.get("lineage_status") == "new")
    print(f"       {continued} continued, {new_count} new")

    # 8. Heat scoring
    print("[8/10] Computing heat scores...")
    topics = _compute_heat_scores(
        topics, candidates, recent_days, baseline_days, anchor_date, min_recent,
    )
    hot_count = sum(1 for t in topics if t.get("is_hot"))
    print(f"       {hot_count} hot topics")

    # 9. LLM labeling (best-effort — failures do not block the pipeline)
    print("[9/10] Generating Chinese topic labels...")
    try:
        labeler = TopicLabeler(config)
        topics = labeler.label_topics(topics, candidates)
        labeled_count = sum(1 for t in topics if t.get("label_zh"))
        print(f"       {labeled_count} topics labeled")
    except Exception as exc:
        print(f"       LLM labeling skipped — {exc}")
        # Ensure every topic has at least a fallback label
        for t in topics:
            t.setdefault("label_zh", t.get("topic_id", "unnamed"))
            t.setdefault("description", "")
            t.setdefault("why_hot", "")
            t.setdefault("keywords", [])

    # 10. Topic anchors + output
    print("[10/10] Computing anchors and writing output...")
    topic_graph_edges = _compute_topic_graph(topics, candidates, hybrid_edges)
    anchor_positions = _compute_anchor_positions(topics, umap_coords)
    _build_output(
        topics, topic_graph_edges, anchor_positions, umap_coords, paper_heat,
        candidates, net_config, anchor_date, embedding_model, dim, umap_config,
        temp_dir,
    )

    # Atomic replace
    _atomic_replace(temp_dir, final_dir)

    print(f"Output: {final_dir}")
    print("=" * 50)
    return final_dir
