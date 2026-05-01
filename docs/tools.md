# Tool reference

All tools take their arguments as keyword args via the MCP protocol. Money fields are always in Kč (the Sklik API uses haléře internally — tools convert for you).

This catalogue lists every tool registered by the server (39 Drak tools + 5 Fénix tools = 44 total when `SKLIK_FENIX_TOKEN` is set, 39 otherwise). Signatures match the registered FastMCP tools in `src/sklik_mcp/tools/`.

## Verification status (2026-05-01)

End-to-end test on the live API: created a test fulltext campaign with
ad group, text ad, three keywords, and a retargeting list; updated /
paused / resumed each; set negative keywords; removed everything.
Sklik soft-deletes (sets `deleted: true`) — there is no hard-remove via
the JSON API.

| Module | Status | Notes |
|---|---|---|
| Accounts | **VERIFIED end-to-end** | current_account, list_managed_accounts, switch_account |
| Campaigns | **VERIFIED end-to-end** | list/get/create/update/pause/resume/remove all confirmed live |
| Ad groups | **VERIFIED end-to-end** | full CRUD confirmed live |
| Ads | **VERIFIED end-to-end** | text ad CRUD confirmed live |
| Ads — dynamic / DSA | **not exposed by Drak v5** | Probed exhaustively on 2026-05-01: `ads.create` rejects `type`/`creativeType`, all alternative methods (`ads.createDynamic`, `dsa.create`, `dynamicAds.create`, `groups.createDynamic`) return 404, `groups.update` rejects DSA-target fields. Sklik's web UI uses a non-public route. The MCP intentionally ships only `create_text_ad`. |
| Keywords | **VERIFIED end-to-end** | full CRUD confirmed live |
| Negative keywords | **VERIFIED** | redesigned: campaign-level only, set-whole-list via `campaigns.update`. Read API not exposed in v5 |
| Stats — `get_account_overview` | **VERIFIED** | live-tested |
| Stats — per-entity | **NOT IMPLEMENTED** | Sklik uses async report-query (`<entity>.createReport` → poll → `<entity>.readReport`); tracked for v0.2 |
| Retargeting | **VERIFIED end-to-end** | full CRUD confirmed live (test list created and removed) |
| Conversions | partially verified | `list_conversions` works; `get_conversion_stats` uses the async report flow (NOT IMPLEMENTED, tracked for v0.2) |
| Fénix / Nákupy | **OAuth + 4 endpoints verified live, 3 blocked by token scope** | OAuth2 refresh→access flow, `/v1/user/me`, `/v1/user/me/credit`, `/v1/sklik/reports/`, `/v1/nakupy/feeds/`, `/v1/nakupy/campaigns/` — all verified live on 2026-05-01 against premise 230104. `/v1/nakupy/shop-items/`, `/v1/nakupy/products/`, `/v1/nakupy/categories/`, `/v1/nakupy/statistics/aggregated` returned 403 with our test token (Sklik gates these behind a granular resource scope; implementation matches OpenAPI spec exactly). |

### Conventions discovered while wiring against live API

- *List/get response columns:* Sklik's default response carries only the bare
  minimum. All `list_*` and `get_*` tools now request a sensible default
  `displayColumns` set so callers see deletes, bid/budget, dates, finalUrl,
  parent IDs, etc.
- *Soft-deletes:* Sklik never hard-removes; `*.remove` flips `deleted: true`.
  All `list_*` tools hide deleted rows by default; pass `include_deleted=True`
  to surface them.
- *Status values:* On the wire, Sklik only knows `active` / `suspend`. The
  public-facing tool API accepts the friendlier `active` / `paused` and maps.
- *Filter struct:* `restrictionFilter` only accepts `ids` and (where
  applicable) nested `campaign: {ids: [...]}` / `group: {ids: [...]}`. Status
  / name filters are applied client-side after fetching the page.
- *Update calls:* `campaigns.update` insists on receiving `type` even on a
  partial update; the tool auto-fetches it. Bid field on groups/keywords is
  `cpc` (not `maxCpc`). Keyword-text field is `name` (not `keyword`). Ad's
  first description field is `description` (not `description1`).

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

### `list_campaigns(status_filter?, name_contains?, include_deleted=False, limit=100, offset=0)`
List campaigns with optional client-side filters. `status_filter` is one of `active|paused`. Soft-deleted campaigns are hidden by default.
Returns: `{"campaigns": [...], "total": int}` (`total` is the post-filter count of returned items).

### `get_campaign(campaign_id: int)`
Returns: `{"campaign": {...} | null}`. Surfaces id, name, type, status, deleted, deleteDate, createDate, budget.dayBudget, startDate, endDate.

### `create_campaign(name, daily_budget_kc, campaign_type, start_date?, end_date?)`
`campaign_type` is one of `fulltext|context|product|video|simple|zbozi` — Sklik requires it.
Returns: `{"campaign_id": int}`

### `update_campaign(campaign_id, name?, daily_budget_kc?, status?)`
The tool auto-fetches the campaign's `type` (Sklik requires it on every update payload).
Returns: `{"updated": true}`

### `pause_campaign(campaign_id)` / `resume_campaign(campaign_id)`
Both auto-fetch type and map status to Sklik's wire `suspend` / `active`.
Returns: `{"paused": true, ...}` or `{"resumed": true, ...}`

### `remove_campaign(campaign_id)`
Returns: `{"removed": true, "campaign_id": int}`. Sklik soft-deletes (sets `deleted: true`); the row stays in `list_campaigns` only when `include_deleted=True`.

## Ad groups (7)

### `list_ad_groups(campaign_id?, status_filter?, name_contains?, include_deleted=False, limit=100, offset=0)`
Returns: `{"groups": [...], "total": int}`. Surfaces id, name, status, maxCpc, deleted, parent campaign id/name.

### `get_ad_group(group_id)`
Returns: `{"group": {...} | null}`

### `create_ad_group(campaign_id, name, max_cpc_kc)`
Bid is sent on the wire as `cpc` (not `maxCpc`).
Returns: `{"group_id": int}`

### `update_ad_group(group_id, name?, max_cpc_kc?, status?)`
Returns: `{"updated": true}`

### `pause_ad_group(group_id)` / `resume_ad_group(group_id)` / `remove_ad_group(group_id)`

## Ads (7)

### `list_ads(group_id?, status?, include_deleted=False, limit=100, offset=0)`
Returns: `{"ads": [...], "total": int}`. Surfaces id, adType, status, headlines, description(s), finalUrl, deleted, parent group/campaign refs.

### `get_ad(ad_id)`
Returns: `{"ad": {...} | null}`

### `create_text_ad(group_id, headline1, headline2, description1, final_url, headline3?, description2?)`
On the wire `description1` is sent as Sklik's `description` field (singular). No `type` field is allowed — Sklik infers ad type from group/fields.
Returns: `{"ad_id": int}`

### `update_ad(ad_id, headline1?, headline2?, headline3?, description1?, description2?, final_url?, status?)`
Returns: `{"updated": true}`

### `pause_ad(ad_id)` / `resume_ad(ad_id)` / `remove_ad(ad_id)`

## Keywords (7)

### `list_keywords(group_id?, status?, include_deleted=False, limit=100, offset=0)`
Returns: `{"keywords": [...], "total": int}`. Surfaces id, name, matchType, status, cpc, deleted, group/campaign refs.

### `get_keyword(keyword_id)`
Returns: `{"keyword": {...} | null}`

### `add_keywords(group_id, keywords: [{keyword, match_type, max_cpc_kc?}])`
Batch add. `match_type` is one of `broad|phrase|exact` (sent verbatim on the wire). On the wire Sklik's keyword-text field is `name` (not `keyword`); the tool maps. The bid field is `cpc` in Kč (converted to haléře).
Returns: `{"keyword_ids": [int, ...]}` — read from the response's `positiveKeywordIds` field.

### `update_keyword(keyword_id, max_cpc_kc?, status?)`
Returns: `{"updated": true}`

### `pause_keyword(keyword_id)` / `resume_keyword(keyword_id)` / `remove_keyword(keyword_id)`

## Negative keywords (1) — VERIFIED, but with v5 caveats

Sklik v5 has NO separate JSON-RPC namespace for negative keywords — the
guess methods (`campaigns.getNegativeKeywords` etc.) all return 404. The
real shape:

- Negatives are a field on the campaign struct: `negativeKeywords`.
- They are written via `campaigns.update` and replace the whole list at
  once (no incremental add/remove).
- Element shape: `{"name": str, "matchType": "negativeBroad" |
  "negativePhrase" | "negativeExact"}` — note the prefix vs regular
  keywords' bare match types.
- Available only for campaign types `context`, `fulltext`, `product`,
  `simple` — NOT `zbozi`. For Shopping, use product groups (Fénix).
- Reading them back is not exposed by the v5 JSON API.
- Group-scoped negatives are not supported in v5.

### `set_campaign_negative_keywords(campaign_id, campaign_type, keywords: [{name, match_type}])`
Replaces the entire negative-keyword list. Pass `[]` to clear. `campaign_type` must be one of `context|fulltext|product|simple`.
Returns: `{"updated": true, "count": int}`

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

## Retargeting (4) — VERIFIED end-to-end 2026-05-01

Method namespace is `retargeting.lists.*`. Each item in the list response carries `listId` (not `id`).

### `list_retargeting_lists()`
Returns: `{"retargeting_lists": [{"listId": int, "name": str, "status": str, "deleted": bool}]}`

### `create_retargeting_list(name, membership_days=30, use_historic_data=False, take_all_users=True)`
Returns: `{"retargeting_id": int}`. On the wire Sklik wraps everything in an `attributes` struct.

### `update_retargeting_list(retargeting_id, name?, membership_days?)`
Returns: `{"updated": true}`. Element key on the wire is `listId` (not `id`); editable fields nest under `attributes`.

### `remove_retargeting_list(retargeting_id)`
Returns: `{"removed": true, "retargeting_id": int}`. On the wire Sklik takes a bare `[id, ...]` list (not `{"id": ...}`).

## Conversions (2)

### `list_conversions()`  — VERIFIED
Returns: `{"conversions": [...]}`

### `get_conversion_stats(conversion_id, date_from, date_to)` — UNVERIFIED
Likely uses Sklik's async report flow (not implemented yet). Will return raw response or 404 until v0.2.

## Fénix / Sklik Nákupy (5) — wired against unified `/v1/` API

The Fénix tools talk to the unified `/v1/` REST API (OpenAPI spec at
`https://api.sklik.cz/v1/openapi.json`). They are only registered when
`SKLIK_FENIX_TOKEN` is set; without it, the tools simply don't appear,
keeping the Drak tools usable on their own.

**Auth:** A two-step OAuth2 flow. The user provides a long-lived
refresh JWT (from the Sklik web UI). On first use, the client exchanges
it for a short-lived access token via `POST /v1/user/token`
(form-encoded, `grant_type=client_credentials`, refresh JWT in the
Authorization header). The access token is cached and reused; we
re-exchange when it nears expiry.

**Premise IDs:** Sklik Nákupy is organised by *provozovna* (premise),
not Drak campaign id. Most calls take a `premise_id`. Discover yours
through Sklik's Nákupy admin UI; we don't yet expose a "list premises"
helper (tracked for v0.1.x).

**Live verification status (2026-05-01):** OAuth2 refresh→access
exchange, `/user/me`, `/user/me/credit`, `/sklik/reports/`,
`/nakupy/feeds/` and `/nakupy/campaigns/` all round-tripped successfully
against premise 230104. The remaining `/nakupy/*` endpoints
(shop-items, products, categories, statistics/aggregated) returned
**403 Forbidden** — Sklik gates those behind a granular resource scope
that has to be granted at refresh-token generation time, even when the
OAuth `scope` claim already says `r rw rwa`. The implementation matches
the OpenAPI spec; supply a token with the right resource scope and
these tools should "just work". Use `get_fenix_user_info` first to see
which scopes your token holds.

### `get_fenix_user_info()`
Returns the currently authorized `/v1/` user (`userId`, `userName`, `actor`, `scope`). Sanity-check helper for verifying that `SKLIK_FENIX_TOKEN` is set, valid, and has the scopes you expect — useful before calling any Nákupy-specific tool. Calls `GET /v1/user/me`.

### `list_shop_items(premise_id, item_id?, paired?, product_category_id?, limit=100, offset=0)`
List shop items (rows from your XML feed) for a Nákupy premise.
Returns the raw `ListShopItemsResponse` (`{"items": [...]}` etc.).

### `update_shop_item_bid(premise_id, item_id, search_max_cpc_kc?, product_max_cpc_kc?)`
PATCH a single shop item's CPC bids. `searchMaxCpc` covers Seznam Nákupy search results; `productMaxCpc` covers clicks from product detail pages. Bids are decimal Kč (NOT haléře).

### `list_shopping_campaigns(premise_id)`
List Sklik Nákupy campaigns scoped to a premise.

### `get_shopping_stats(premise_id, date_from, date_to, granularity="daily")`
POST to `/nakupy/statistics/aggregated`. Granularity ∈ `daily | weekly | monthly | quarterly | yearly | none`.
