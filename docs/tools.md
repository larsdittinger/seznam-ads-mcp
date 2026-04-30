# Tool reference

All tools take their arguments as keyword args via the MCP protocol. Money fields are always in Kč (the Sklik API uses haléře internally — tools convert for you).

This catalogue lists every tool registered by the server (45 total, grouped by module). Signatures match the registered FastMCP tools in `src/sklik_mcp/tools/`.

## Verification status (2026-04-30)

| Module | Status | Notes |
|---|---|---|
| Accounts | **VERIFIED** | live-tested: login, current_account, list_managed_accounts |
| Campaigns | **VERIFIED** read paths | list_campaigns confirmed live; write paths not yet exercised |
| Ad groups | **VERIFIED** read paths | list_ad_groups confirmed live; response field is `groups` |
| Ads | likely correct | list_ads returned 200 with empty list (test account has no text ads); write paths not exercised |
| Keywords | likely correct | list_keywords returned 200 |
| Negative keywords | **UNVERIFIED** | All three method names (`campaigns.getNegativeKeywords` etc.) returned 404. Real method names TBD. |
| Stats — `get_account_overview` | **VERIFIED** | live-tested |
| Stats — per-entity | **NOT IMPLEMENTED** | Sklik uses async report-query (`<entity>.createReport` → poll → `<entity>.readReport`); tracked for v0.2 |
| Retargeting | **VERIFIED** | namespace fixed to `retargeting.lists.*` |
| Conversions | partially verified | `list_conversions` works; `get_conversion_stats` likely uses async report flow (UNVERIFIED) |
| Fénix | **NOT WORKING** | Fénix uses OAuth2 (refresh→access token), our client sends raw Bearer. Tracked for v0.1.2. |

## Accounts (3)

### `list_managed_accounts()`
List Sklik accounts the API token can manage (impersonate / převtělit). Empty list = no impersonation; you operate as the token owner.
Returns: `{"accounts": [{"user_id": int, "username": str}, ...]}`

### `switch_account(user_id: int)`
Switch active Sklik account (převtělit se / impersonate). Pass `0` to clear.
Returns: `{"active_user_id": int | null}`

### `current_account()`
Returns: `{"active_user_id": int | null, "token_owner_user_id": int | null}`

## Campaigns (7)

### `list_campaigns(status_filter?, name_contains?, limit=100, offset=0)`
List campaigns with optional filters. `status_filter` is one of `active|paused|removed`.
Returns: `{"campaigns": [...], "total": int}` — note: Sklik does not return a `totalCount` field, so `total` is always `0` until v0.2 fixes this.

### `get_campaign(campaign_id: int)`
Returns: `{"campaign": {...} | null}`

### `create_campaign(name, daily_budget_kc, currency="CZK", start_date?, end_date?)`
Returns: `{"campaign_id": int}`

### `update_campaign(campaign_id, name?, daily_budget_kc?, status?)`
Returns: `{"updated": true}`

### `pause_campaign(campaign_id)` / `resume_campaign(campaign_id)`
Returns: `{"paused": true, ...}` or `{"resumed": true, ...}`

### `remove_campaign(campaign_id)`
Returns: `{"removed": true, "campaign_id": int}`

## Ad groups (7)

### `list_ad_groups(campaign_id?, status_filter?, name_contains?, limit=100, offset=0)`
Returns: `{"groups": [...], "total": int}`

### `get_ad_group(group_id)`
Returns: `{"group": {...} | null}`

### `create_ad_group(campaign_id, name, max_cpc_kc)`
Returns: `{"group_id": int}`

### `update_ad_group(group_id, name?, max_cpc_kc?, status?)`
Returns: `{"updated": true}`

### `pause_ad_group(group_id)` / `resume_ad_group(group_id)` / `remove_ad_group(group_id)`

## Ads (8)

### `list_ads(group_id?, status?, limit=100, offset=0)`
Returns: `{"ads": [...], "total": int}`

### `get_ad(ad_id)`
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

### `get_keyword(keyword_id)`
Returns: `{"keyword": {...} | null}`

### `add_keywords(group_id, keywords: [{keyword, match_type, max_cpc_kc?}])`
Batch add. `match_type` is one of `broad|phrase|exact` (mapped internally to Sklik's `broad|phraseMatch|exactMatch`).
Returns: `{"keyword_ids": [int, ...]}`

### `update_keyword(keyword_id, max_cpc_kc?, status?)`
Returns: `{"updated": true}`

### `pause_keyword(keyword_id)` / `resume_keyword(keyword_id)` / `remove_keyword(keyword_id)`

## Negative keywords (3) — UNVERIFIED

These tools were implemented against guessed method names. **Live testing on 2026-04-30 returned 404 for `campaigns.getNegativeKeywords`, `campaigns.negativeKeywords.list`, and similar.** The real Sklik method names need to be discovered (likely under a different namespace, possibly attached via `campaigns.update`/`groups.update`). Tracked for v0.1.1.

### `list_negative_keywords(scope, scope_id)`
### `add_negative_keywords(scope, scope_id, keywords: list[str])`
### `remove_negative_keyword(scope, scope_id, negative_keyword_id)`

## Stats (1)

The previous `get_stats(entity, entity_ids, ...)` tool was REMOVED in this iteration because Sklik does not provide synchronous per-entity stats. Per-entity reports use an asynchronous query model that needs proper implementation:

```
<entity>.createReport(filter)  → returns reportId
stats.status(reportId)         → poll until ready
<entity>.readReport(reportId)  → fetch the data
```

This is a sizeable feature and is **tracked for v0.2**.

### `get_account_overview(date_from, date_to, granularity="total")`
Account-level performance rollup. Synchronous, returns immediately.
- `granularity` ∈ `hourly|daily|weekly|monthly|total`
- Dates are ISO `YYYY-MM-DD` (inclusive)

Returns: `{"report": [{"date": str, "impressions": int, "clicks": int, "ctr": float, "cpc": int, "price": int, "price_kc": float, ...}]}`

The `report` array has 1 row for `total`, N rows for `daily`, etc. Money field is `price` (haléře); `price_kc` is added in Kč.

## Retargeting (4) — VERIFIED 2026-04-30

Method namespace is `retargeting.lists.*`. Response field is `lists` (not `retargetingLists`).

### `list_retargeting_lists()`
Returns: `{"retargeting_lists": [...]}`

### `create_retargeting_list(name, membership_lifespan_days=30)`
Returns: `{"retargeting_id": int}`

### `update_retargeting_list(retargeting_id, name?, membership_lifespan_days?)`
Returns: `{"updated": true}`

### `remove_retargeting_list(retargeting_id)`
Returns: `{"removed": true, "retargeting_id": int}`

## Conversions (2)

### `list_conversions()`  — VERIFIED
Returns: `{"conversions": [...]}`

### `get_conversion_stats(conversion_id, date_from, date_to)` — UNVERIFIED
Likely uses Sklik's async report flow (not implemented yet). Will return raw response or 404 until v0.2.

## Fénix shopping (3) — BROKEN as of v0.1.0

Fénix is Sklik's REST endpoint for Seznam Nákupy. **The token format is OAuth2 (a JWT refresh_token), not the Drak API token.** The current `FenixClient` sends the refresh_token as a Bearer header directly, which Fénix rejects. Need to add a refresh→access token exchange step. **Tracked for v0.1.2.**

### `list_product_groups(campaign_id: int)`
### `update_product_group_bid(product_group_id, max_cpc_kc)`
### `get_shopping_stats(date_from, date_to, group_by="day")`
