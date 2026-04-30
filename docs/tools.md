# Tool reference

All tools take their arguments as keyword args via the MCP protocol. Money fields are always in Kč unless suffixed `_haler` (the Sklik API uses haléře internally — tools convert for you).

This catalogue lists every tool registered by the server (46 total, grouped by module). Signatures match the registered FastMCP tools in `src/sklik_mcp/tools/`.

## Accounts (3)

### `list_managed_accounts()`
List Sklik accounts the API token can manage (impersonate / převtělit).
Returns: `{"accounts": [{"user_id": int, "username": str}, ...]}`

### `switch_account(user_id: int)`
Switch active Sklik account (převtělit se / impersonate). Pass `0` to clear and use the token owner's own account.
Returns: `{"active_user_id": int | null}`

### `current_account()`
Show which account is currently active.
Returns: `{"active_user_id": int | null, "token_owner_user_id": int | null}`

## Campaigns (7)

### `list_campaigns(status_filter?, name_contains?, limit=100, offset=0)`
List campaigns with optional filters. `status_filter` is one of `active|paused|removed`.
Returns: `{"campaigns": [...], "total": int}`

### `get_campaign(campaign_id: int)`
Returns: `{"campaign": {...} | null}`

### `create_campaign(name, daily_budget_kc, currency="CZK", start_date?, end_date?)`
Returns: `{"campaign_id": int}`

### `update_campaign(campaign_id, name?, daily_budget_kc?, status?)`
Returns: `{"updated": true}`

### `pause_campaign(campaign_id: int)` / `resume_campaign(campaign_id: int)`
Returns: `{"paused": true, "campaign_id": int}` or `{"resumed": true, "campaign_id": int}`

### `remove_campaign(campaign_id: int)`
Returns: `{"removed": true, "campaign_id": int}`

## Ad groups (7)

### `list_ad_groups(campaign_id?, status_filter?, name_contains?, limit=100, offset=0)`
Returns: `{"groups": [...], "total": int}`

### `get_ad_group(group_id: int)`
Returns: `{"group": {...} | null}`

### `create_ad_group(campaign_id, name, max_cpc_kc)`
Returns: `{"group_id": int}`

### `update_ad_group(group_id, name?, max_cpc_kc?, status?)`
Returns: `{"updated": true}`

### `pause_ad_group(group_id)` / `resume_ad_group(group_id)`
### `remove_ad_group(group_id)`

## Ads (8)

### `list_ads(group_id?, status?, limit=100, offset=0)`
Returns: `{"ads": [...], "total": int}`

### `get_ad(ad_id: int)`
Returns: `{"ad": {...} | null}`

### `create_text_ad(group_id, headline1, headline2, description1, final_url, headline3?, description2?)`
Returns: `{"ad_id": int}`

### `create_dynamic_ad(group_id, final_url, description1?)`
Returns: `{"ad_id": int}`

### `update_ad(ad_id, headline1?, headline2?, headline3?, description1?, description2?, final_url?, status?)`
Returns: `{"updated": true}`

### `pause_ad(ad_id)` / `resume_ad(ad_id)` / `remove_ad(ad_id)`

## Keywords (7)

### `list_keywords(group_id?, status?, limit=100, offset=0)`
Returns: `{"keywords": [...], "total": int}`

### `get_keyword(keyword_id: int)`
Returns: `{"keyword": {...} | null}`

### `add_keywords(group_id, keywords: [{keyword, match_type, max_cpc_kc?}])`
Batch add. `match_type` is one of `broad|phrase|exact` (mapped internally to Sklik's `broad|phraseMatch|exactMatch`).
Returns: `{"keyword_ids": [int, ...]}`

### `update_keyword(keyword_id, max_cpc_kc?, status?)`
Returns: `{"updated": true}`

### `pause_keyword(keyword_id)` / `resume_keyword(keyword_id)` / `remove_keyword(keyword_id)`

## Negative keywords (3)

### `list_negative_keywords(scope, scope_id)`
`scope` is `"campaign"` or `"group"`.
Returns: `{"negative_keywords": [...]}`

### `add_negative_keywords(scope, scope_id, keywords: list[str])`
Returns: `{"added": int, "ids": [int, ...]}`

### `remove_negative_keyword(scope, scope_id, negative_keyword_id)`
Returns: `{"removed": true}`

## Stats (2)

### `get_stats(entity, entity_ids, date_from, date_to, granularity="total")`
`entity` ∈ `campaign|group|ad|keyword`. `granularity` ∈ `hourly|daily|weekly|monthly|total`. Dates are ISO `YYYY-MM-DD` (inclusive). Money fields in returned rows are augmented with `_kc` (Kč) versions.
Returns: `{"report": [{"id": int, "stats": [{"date": str, "impressions": int, "clicks": int, "spend": int, "spend_kc": float, ...}]}]}`

### `get_account_overview(date_from, date_to)`
Account-level rollup for the window.
Returns: `{"impressions": int, "clicks": int, "spend": int, "spend_kc": float, ...}`

## Retargeting (4)

### `list_retargeting_lists()`
Returns: `{"retargeting_lists": [...]}`

### `create_retargeting_list(name, membership_lifespan_days=30)`
Returns: `{"retargeting_id": int}`

### `update_retargeting_list(retargeting_id, name?, membership_lifespan_days?)`
Returns: `{"updated": true}`

### `remove_retargeting_list(retargeting_id)`
Returns: `{"removed": true, "retargeting_id": int}`

## Conversions (2)

### `list_conversions()`
Returns: `{"conversions": [...]}`

### `get_conversion_stats(conversion_id, date_from, date_to)`
Returns: conversion stats dict with `_kc` Kč fields where applicable.

## Fénix shopping (3)

Fénix is Sklik's REST endpoint for Seznam Nákupy. These tools talk to a separate REST service from the Drak JSON-RPC tools above and use the same `SKLIK_API_TOKEN` as a Bearer token.

### `list_product_groups(campaign_id: int)`
Returns: `{"product_groups": [...]}`

### `update_product_group_bid(product_group_id, max_cpc_kc)`
Returns: raw Fénix API response.

### `get_shopping_stats(date_from, date_to, group_by="day")`
`group_by` ∈ `day|campaign|productGroup`.
Returns: raw shopping stats response from Fénix.
