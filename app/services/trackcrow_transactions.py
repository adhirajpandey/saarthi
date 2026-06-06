"""Trackcrow transaction search service used by the MCP runtime."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator

from shared.settings import McpSettings

logger = logging.getLogger(__name__)


class TransactionSearchFilters(BaseModel):
    """Validated MCP transaction search filters."""

    recipient: str | None = None
    category: str | None = None
    keyword: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    limit: int = Field(default=10, ge=1, le=50)

    @model_validator(mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> object:
        if not isinstance(value, Mapping):
            return value
        payload = dict(value)
        for field in ("recipient", "category", "keyword", "start_date", "end_date"):
            field_value = payload.get(field)
            if isinstance(field_value, str):
                stripped = field_value.strip()
                payload[field] = stripped or None
        limit_value = payload.get("limit")
        if isinstance(limit_value, int):
            payload["limit"] = max(1, min(50, limit_value))
        return payload

    @model_validator(mode="after")
    def _validate_at_least_one_filter(self) -> "TransactionSearchFilters":
        if not any(
            [
                self.recipient,
                self.category,
                self.keyword,
                self.start_date,
                self.end_date,
            ]
        ):
            raise ValueError("at least one filter must be provided")
        return self


def _parse_bound(value: str, *, field_name: str, end_of_day: bool) -> datetime:
    try:
        if len(value) == 10:
            parsed_date = datetime.strptime(value, "%Y-%m-%d").date()
            parsed = datetime.combine(
                parsed_date,
                time.max if end_of_day else time.min,
                tzinfo=UTC,
            )
        else:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            else:
                parsed = parsed.astimezone(UTC)
        return parsed
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO-8601 date or datetime") from exc


def _serialize_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    normalized = value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    return normalized.isoformat().replace("+00:00", "Z")


def _serialize_transaction_row(row: Mapping[str, Any]) -> dict[str, Any]:
    amount = row.get("amount")
    if isinstance(amount, Decimal):
        amount = float(amount)

    return {
        "id": row["id"],
        "timestamp": _serialize_timestamp(row.get("timestamp")),
        "amount": amount,
        "recipient": row.get("recipient"),
        "recipient_name": row.get("recipient_name"),
        "category": row.get("category"),
        "subcategory": row.get("subcategory"),
        "type": row.get("type"),
        "remarks": row.get("remarks"),
        "location": row.get("location"),
    }


def _load_psycopg() -> tuple[Any, Any]:
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ImportError as exc:
        raise RuntimeError("psycopg is required for Trackcrow transaction search") from exc
    return psycopg, dict_row


def _fetch_transaction_rows(
    *,
    dsn: str,
    user_uuid: str,
    filters: TransactionSearchFilters,
    start_bound: datetime | None,
    end_bound: datetime | None,
) -> Sequence[Mapping[str, Any]]:
    psycopg, dict_row = _load_psycopg()

    clauses = ['t."user_uuid" = %s']
    params: list[Any] = [user_uuid]

    if filters.recipient:
        clauses.append('(t."recipient" ILIKE %s OR t."recipient_name" ILIKE %s)')
        recipient_like = f"%{filters.recipient}%"
        params.extend([recipient_like, recipient_like])

    if filters.keyword:
        clauses.append(
            '(t."recipient" ILIKE %s OR t."recipient_name" ILIKE %s OR t."remarks" ILIKE %s)'
        )
        keyword_like = f"%{filters.keyword}%"
        params.extend([keyword_like, keyword_like, keyword_like])

    if filters.category:
        clauses.append('c."name" ILIKE %s')
        params.append(filters.category)

    if start_bound:
        clauses.append('t."timestamp" >= %s')
        params.append(start_bound)

    if end_bound:
        clauses.append('t."timestamp" <= %s')
        params.append(end_bound)

    params.append(filters.limit)

    query = f"""
        SELECT
            t."id",
            t."timestamp",
            t."amount",
            t."recipient",
            t."recipient_name",
            c."name" AS category,
            s."name" AS subcategory,
            t."type",
            t."remarks",
            t."location"
        FROM "public"."transaction" t
        LEFT JOIN "public"."category" c ON c."id" = t."categoryId"
        LEFT JOIN "public"."subcategory" s ON s."id" = t."subcategoryId"
        WHERE {" AND ".join(clauses)}
        ORDER BY t."timestamp" DESC
        LIMIT %s
    """

    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()


def search_trackcrow_transactions(
    *,
    settings: McpSettings,
    recipient: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search Trackcrow transactions for the configured MCP user."""

    try:
        filters = TransactionSearchFilters.model_validate(
            {
                "recipient": recipient,
                "category": category,
                "keyword": keyword,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
            }
        )
    except ValidationError as exc:
        message = exc.errors()[0]["msg"] if exc.errors() else "invalid search filters"
        raise ValueError(message) from exc

    start_bound = (
        _parse_bound(filters.start_date, field_name="start_date", end_of_day=False)
        if filters.start_date
        else None
    )
    end_bound = (
        _parse_bound(filters.end_date, field_name="end_date", end_of_day=True)
        if filters.end_date
        else None
    )

    if start_bound and end_bound and start_bound > end_bound:
        raise ValueError("start_date must be earlier than or equal to end_date")

    try:
        rows = _fetch_transaction_rows(
            dsn=settings.trackcrow_db_url,
            user_uuid=settings.trackcrow_mcp_user_uuid,
            filters=filters,
            start_bound=start_bound,
            end_bound=end_bound,
        )
    except Exception:  # pragma: no cover - runtime failures depend on environment
        logger.exception("search_trackcrow_transactions - query failed")
        return {
            "success": False,
            "message": "Failed to search Trackcrow transactions",
        }

    transactions = [_serialize_transaction_row(row) for row in rows]
    return {
        "success": True,
        "count": len(transactions),
        "filters": filters.model_dump(),
        "transactions": transactions,
    }
