# Current provider: XOOMAR

Import `XOOMAR.postman_collection.json`. No key or environment is needed. Send requests 1 and 2; both should return HTTP 200 and a JSON `data` array. Request 2 uses the same UTC date parameters as the bot for the current Bangkok week. The bot additionally filters exact Bangkok date boundaries. Optional collection variables `from_date` and `to_date` allow custom dates. No Discord messages are sent.

The FMP files below are legacy diagnostics; the bot no longer uses FMP.

# Standalone FMP diagnostics in Postman

1. In Postman, choose **Import → Files** and import both JSON files in this folder.
2. Select the **FMP local diagnostics** environment.
3. Open its variables and set `FMP_API_KEY` to your current key locally. Keep it out of shared/exported files.
4. Leave `from_date` and `to_date` blank to calculate the bot's current Bangkok week automatically, or enter `YYYY-MM-DD` UTC dates to test a specific range.
5. Open the collection and send requests **1, 2, 3** individually. All use **GET**, no request body, and query-parameter authentication, matching the bot.

| Result | Interpretation |
| --- | --- |
| 1 succeeds; 2 and 3 return 402 | Key works for symbol search; calendar requests are restricted. |
| 2 succeeds; 3 returns 402 | Explicit date filters/range are likely restricted; share the response error text with FMP support to confirm. |
| 3 succeeds with a JSON array | Standalone calendar request works. Ensure Modal uses this same key, workspace, and secret; retest the bot. |
| 401 | Check the key and selected environment. |
| 429 | Rate limit; wait before retrying. |

For a 402, inspect **Body → Pretty/JSON** and read FMP's exact message. Adding billing details alone does not prove that a subscription is active or includes this request. Verify the active plan and key/account in the FMP dashboard. If needed, give FMP support the endpoint, date parameters, HTTP status, response error text, and active plan name. Do not share the API key or a full request URL containing it.

The collection's tests expect HTTP 200 and an array, so access errors intentionally appear as failed tests. An empty array means the request succeeded with no rows returned; it does not demonstrate complete calendar coverage.

These requests do not access Modal, send Discord messages, or change the bot's stored state. The files were checked locally for structure; live account access must be tested in Postman with your key.

Official reference: https://site.financialmodelingprep.com/developer/docs
