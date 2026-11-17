# Logging

The SDK logs to the standard-library logger **`bunny_cdn_sdk`**, at `DEBUG` only. It never adds
handlers or changes levels itself, so by default it prints nothing. Your application decides
what is shown and where it goes.

Use it to see why a request failed, when retries happen, and where Bunny's responses differ from
its published API spec.

- [Turn it on](#turn-it-on)
- [Events](#events)
- [Secrets](#secrets)
- [Recipes](#recipes): JSON lines, structlog apps, failures only, spec drift in tests
- [Cost](#cost)

## Turn it on

```python
import logging

logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("bunny_cdn_sdk").setLevel(logging.DEBUG)
```

Each event is one line of `key='value'` pairs:

```text
DEBUG bunny_cdn_sdk: event='request_failed' method='GET' url='https://api.bunny.net/pullzone/1'
  request_headers={..., 'accesskey': '***', ...} request_body=None status=500
  response_headers={...} response_body={'Message': 'boom'}
```

The CLI does the same with `bunnycdn --debug ...` (or `BUNNY_DEBUG=1`), logging to stderr so
`--output-format json` output on stdout stays clean.

## Events

Every record carries the event's fields twice:

- **As the message:** readable `key='value'` text, for any handler.
- **As `record.bunny_event`:** a dict, for JSON or structlog formatters. Its `event` key holds
  the event name. It is redacted the same way as the message.

| `event` | When | Fields |
|---|---|---|
| `request_failed` | The API answered with an HTTP error (4xx/5xx), just before the SDK raises `BunnyAPIError` or a subclass | `method`, `url`, `status`, `request_headers`, `request_body`, `response_headers`, `response_body` |
| `request_error` | The request never got an answer: connection error or timeout, before `BunnyConnectionError` / `BunnyTimeoutError` | `method`, `url`, `error` |
| `request_retry` | Before each retry, only when retries are on (`max_retries=` or your own `RetryTransport`) | `method`, `url`, `attempt`, `max_retries`, `delay` (seconds), `reason` (e.g. `HTTP 503`, or the network error) |
| `response_type_mismatch` | A successful response doesn't match the spec type the method is annotated with | `method`, `url`, `spec_type`, `mismatches` (up to 20 entries like `$.Items[0].Size: expected float, got str`), `more` (how many were cut) |
| `response_type_check_skipped` | The type check itself failed; the call is unaffected | `method`, `url`, plus the traceback |

**Bodies:**
- JSON bodies are logged as parsed values.
- Other bodies are logged as text, cut at 2,000 characters.
- A streamed body that can't be re-read is shown as `<stream>`.

**Type mismatches never raise.** The return types (`bunny_cdn_sdk.models.*`) are static types
generated from Bunny's specs, and those specs drift from what the API returns. A mismatch tells
you the spec, or its generated type, is wrong for that response. Your data is still returned
unchanged.

## Secrets

Before anything is logged, the SDK replaces with `***`:

- **Secret-named keys:** headers and JSON fields at any depth whose names contain `key`,
  `password`, `secret`, `token`, `authorization`, `signature`, `credential` or `cookie`. That
  covers the `AccessKey` header, `Password`, `ReadOnlyPassword`, `ZoneSecurityKey` and API key
  fields.
- **URL query parameters** with secret-like names, e.g. `?token=…` and `api_key=…`.

**What redaction can't catch:** it works by name. A secret inside a non-JSON text body, or under
a field name not on that list, is logged as-is. DEBUG output holds full request and response
bodies, so treat it as sensitive anyway: don't ship it to shared log stores by default.

## Recipes

### JSON lines, standard library only

```python
import json
import logging


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        fields = getattr(record, "bunny_event", {"event": record.getMessage()})
        return json.dumps({"level": record.levelname, "logger": record.name, **fields}, default=str)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
sdk_logger = logging.getLogger("bunny_cdn_sdk")
sdk_logger.addHandler(handler)
sdk_logger.setLevel(logging.DEBUG)
sdk_logger.propagate = False  # don't print the same event again through root handlers
```

### Apps that already use structlog

The SDK never calls `structlog.configure()`, so your configuration is untouched. Its events reach
you as standard-library records. To render them with your structlog pipeline, add the fields
from `record.bunny_event` in `ProcessorFormatter`'s `foreign_pre_chain`:

```python
import logging

import structlog


def merge_bunny_event(_logger, _method, event_dict):
    fields = getattr(event_dict.get("_record"), "bunny_event", None)
    if fields:
        event_dict.update(fields)  # event, method, url, status, ...
    return event_dict


handler = logging.StreamHandler()
handler.setFormatter(
    structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            merge_bunny_event,
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),  # or structlog.dev.ConsoleRenderer()
        ],
    )
)
logging.getLogger().addHandler(handler)
logging.getLogger("bunny_cdn_sdk").setLevel(logging.DEBUG)
```

### Only failed requests

Every SDK event is DEBUG, so choose events by name, not by level:

```python
import logging


class BunnyFailures(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        event = getattr(record, "bunny_event", {}).get("event")
        return event in {"request_failed", "request_error", "request_retry"}


handler = logging.StreamHandler()
handler.addFilter(BunnyFailures())
sdk_logger = logging.getLogger("bunny_cdn_sdk")
sdk_logger.addHandler(handler)
sdk_logger.setLevel(logging.DEBUG)
sdk_logger.propagate = False
```

Every failure still raises an exception: `BunnyAPIError` and its subclasses, or
`BunnyConnectionError`/`BunnyTimeoutError`. Logging adds the request and response detail that
the exception message leaves out.

### Seeing retries

Retries are off by default. When on, the SDK retries:

- **Any request:** 429s (honouring `Retry-After`) and connection errors.
- **Only GET, HEAD, OPTIONS and DELETE:** 5xx responses and timeouts, because those methods are
  safe to repeat.

Each retry logs a `request_retry` event:

```python
from bunny_cdn_sdk import CoreClient

core = CoreClient(api_key="...", max_retries=3)  # backoff_base=0.5 by default
```

### Catching spec drift in your tests

With pytest's `caplog`, a test can fail when a real response no longer matches the SDK's types.
That is useful in an integration suite run against a test account:

```python
import logging


def test_pull_zones_match_spec(caplog, core_client):
    with caplog.at_level(logging.DEBUG, logger="bunny_cdn_sdk"):
        core_client.list_pull_zones()
    drift = [
        r.bunny_event
        for r in caplog.records
        if getattr(r, "bunny_event", {}).get("event") == "response_type_mismatch"
    ]
    assert drift == []
```

## Cost

When the `bunny_cdn_sdk` logger isn't enabled for DEBUG, logging costs one level check per
request. Detail fields and type checks are only built when DEBUG is on.

With DEBUG on, every JSON response is walked against its type, and failed requests log full
bodies. That's fine for debugging, scripts and test suites. Think twice before running it on
a busy production path: enable it on demand, for example from an environment variable:

```python
import logging
import os

if os.environ.get("BUNNY_DEBUG"):
    logging.getLogger("bunny_cdn_sdk").setLevel(logging.DEBUG)
```
