---
name: bunny-cdn-sdk-logging
description: Turn on and use the bunny-cdn-sdk Python library's debug logging. Use when code calls bunny_cdn_sdk (CoreClient, StorageClient, ShieldClient, LoggingClient, PartnerClient) and you need to see why a Bunny API call failed (BunnyAPIError, 4xx/5xx, timeouts), watch retries, check responses against the SDK's types, or wire the SDK's logs into an app's logging, JSON logs or structlog. Also covers what the logs redact, and how to test for spec drift with caplog.
---

# Logging with bunny-cdn-sdk

The SDK logs to the **standard-library logger `bunny_cdn_sdk`, at DEBUG only**, and is silent by
default. It never adds handlers, never changes levels and never calls `structlog.configure()`.
Turning it on is always one level change, and doesn't affect any other logging.

Full guide with all recipes:
https://github.com/yolabingo/bunny-cdn-python-sdk/blob/main/docs/LOGGING.md

## Debugging a failing call

1. **Turn on DEBUG for the SDK logger only.** Don't raise the root level:

   ```python
   import logging
   logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
   logging.getLogger("bunny_cdn_sdk").setLevel(logging.DEBUG)
   ```

   For the CLI, use `bunnycdn --debug <command>` or `BUNNY_DEBUG=1`. It logs to stderr.

2. **Run the call again and read the event logged just before the exception.**

   | `event` | Means | Look at |
   |---|---|---|
   | `request_failed` | Bunny answered with an HTTP error; `BunnyAPIError` (or a subclass) follows | `status`, `response_body` (Bunny's `Message`/`ErrorKey`), `request_body` (what was actually sent), `url` |
   | `request_error` | No answer: connection error or timeout | `error` |
   | `request_retry` | A retry is coming (only with `max_retries=` or a `RetryTransport`) | `attempt`, `delay`, `reason` |
   | `response_type_mismatch` | The call succeeded, but the data doesn't match the SDK's spec type | `mismatches`, such as `$.Items[0].Size: expected float, got str` |

3. **Diagnose from the bodies, not the exception text.**
   - A 400's `response_body` usually names the bad field.
   - Compare `request_body` with the method's `Unpack[...]` request type in
     `bunny_cdn_sdk.models.<api>` for misspelt or wrongly typed fields.
   - **API keys:** the logger redacts them, so a 401 shows `'accesskey': '***'`. Check which key
     the client was given, not the log. A Partner API call needs a partner key; Storage needs the
     zone password.

## Rules

- **Secrets:** the logs show `***` for secret-named headers, fields and URL query parameters
  (AccessKey, Password, ZoneSecurityKey, token, …), but redaction works by name. Even so, never
  paste raw DEBUG output into issues or chats without reading it first: bodies are logged in full.
- **Mismatches never raise.** The SDK returns plain dicts typed with TypedDicts generated from
  Bunny's OpenAPI specs, which drift. Treat `response_type_mismatch` as "the spec is wrong for
  this response". Don't use it to reject data, and don't write `cast`s to quiet it.
- **Production:** keep DEBUG off on busy paths. It walks every response against its type and
  logs full bodies of failed requests. Enable it on demand, for example from an environment
  variable.
- **Exceptions are still the contract.** Handle `BunnyAPIError` and its subclasses
  (`BunnyNotFoundError`, `BunnyRateLimitError`, …) and `BunnyConnectionError` in code. Logging
  is for diagnosis, not control flow.

## Wiring it into an app

Every record has the event's fields twice: as a readable `key='value'` message, and as the dict
`record.bunny_event`, already redacted, with an `event` key. Use the dict for structured output.

**JSON lines (stdlib only):**

```python
class JsonFormatter(logging.Formatter):
    def format(self, record):
        fields = getattr(record, "bunny_event", {"event": record.getMessage()})
        return json.dumps({"level": record.levelname, "logger": record.name, **fields}, default=str)
```

**An app that uses structlog:** add this to `ProcessorFormatter(foreign_pre_chain=[...])`:

```python
def merge_bunny_event(_logger, _method, event_dict):
    fields = getattr(event_dict.get("_record"), "bunny_event", None)
    if fields:
        event_dict.update(fields)
    return event_dict
```

**Only failures:** every event is DEBUG, so filter by name with a `logging.Filter` that checks
`record.bunny_event.get("event") in {"request_failed", "request_error", "request_retry"}`.

When you attach a handler to `bunny_cdn_sdk` itself, set `propagate = False`, or root handlers
will print every event twice.

## Testing for spec drift

```python
def test_zones_match_spec(caplog, core_client):
    with caplog.at_level(logging.DEBUG, logger="bunny_cdn_sdk"):
        core_client.list_pull_zones()
    assert [r.bunny_event for r in caplog.records
            if getattr(r, "bunny_event", {}).get("event") == "response_type_mismatch"] == []
```
