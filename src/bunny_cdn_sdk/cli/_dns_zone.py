"""DNS zone CLI sub-app (includes record sub-commands)."""

from __future__ import annotations

import ipaddress

import typer
from rich.table import Table
from rich.text import Text

from bunny_cdn_sdk import core
from bunny_cdn_sdk.cli._options import SET_HELP, examples
from bunny_cdn_sdk.cli._output import (
    api_client,
    console,
    output_result,
    parse_set_pairs,
    sdk_errors,
)
from bunny_cdn_sdk.models.core import AddDnsRecordModel

dns_zone_app = typer.Typer(no_args_is_help=True, help="Manage Bunny CDN DNS zones.")
record_app = typer.Typer(no_args_is_help=True, help="Manage DNS records within a zone.")
dns_zone_app.add_typer(record_app, name="record")

_ZONE_COLUMNS = ["Domain", "RecordsCount", "Id"]
_RECORD_COLUMNS = ["Name", "Type", "Value", "Id"]
_LIST_COLUMNS = ["Id", "Name", "Type", "Value", "Ttl", "Priority"]
# Spec DnsRecordTypes x-enumNames; the API takes the index (0 = A).
_RECORD_TYPES = (
    "A", "AAAA", "CNAME", "TXT", "MX", "Redirect", "Flatten", "PullZone",
    "SRV", "CAA", "PTR", "Script", "NS", "SVCB", "HTTPS", "TLSA",
)  # fmt: skip


_MX, _SRV = _RECORD_TYPES.index("MX"), _RECORD_TYPES.index("SRV")
_IP_VERSION = {_RECORD_TYPES.index("A"): 4, _RECORD_TYPES.index("AAAA"): 6}


def _record_type(name: str, hint: str = "--type") -> int:
    upper: list[str] = [t.upper() for t in _RECORD_TYPES]
    if name.upper() not in upper:
        msg = f"unknown record type {name!r}; one of: {', '.join(_RECORD_TYPES)}"
        raise typer.BadParameter(msg, param_hint=hint)
    return upper.index(name.upper())


def _record_value(record_type: int, value: str, hint: str = "--value") -> str:
    """A/AAAA values must be an IPv4/IPv6 address; returned normalized. Others pass through."""
    version = _IP_VERSION.get(record_type)
    if version is None:
        return value
    try:
        ip = ipaddress.ip_address(value.strip())
    except ValueError:
        ip = None
    if ip is None or ip.version != version:
        kind = _RECORD_TYPES[record_type]
        msg = f"{kind} record value must be an IPv{version} address, got {value!r}"
        raise typer.BadParameter(msg, param_hint=hint)
    return str(ip)


def _type_name(value: object) -> object:
    """API type int -> name; an out-of-range or non-int value is returned as is."""
    if isinstance(value, int) and 0 <= value < len(_RECORD_TYPES):
        return _RECORD_TYPES[value]
    return value


def _check_srv_fields(record_type: int, **given: int | None) -> None:
    """Priority/Weight/Port on add: required for MX (priority) and SRV (all), else rejected."""
    needed = {_MX: ("Priority",), _SRV: ("Priority", "Weight", "Port")}.get(record_type, ())
    kind = _RECORD_TYPES[record_type]
    for key, val in given.items():
        hint = f"--{key.lower()}"
        if key in needed and val is None:
            msg = f"{kind} records need {hint}"
            raise typer.BadParameter(msg, param_hint=hint)
        if key not in needed and val is not None:
            msg = f"{hint} does not apply to {kind} records (only MX and SRV; weight/port SRV only)"
            raise typer.BadParameter(msg, param_hint=hint)


@dns_zone_app.command("list")
def list_zones(ctx: typer.Context) -> None:
    """List all DNS zones."""
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        zones = sorted(client.iter_dns_zones(), key=lambda z: z.get("Domain") or "")
        output_result(zones, columns=_ZONE_COLUMNS, json_mode=state.json_output)


@dns_zone_app.command("get")
def get_zone(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="DNS zone ID"),
) -> None:
    """Get a DNS zone by ID."""
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        zone = client.get_dns_zone(id)
        output_result(zone, columns=_ZONE_COLUMNS, json_mode=state.json_output)


@dns_zone_app.command(
    "create",
    epilog=examples("bunnycdn dns-zone create --domain example.com"),
)
def create_zone(
    ctx: typer.Context,
    domain: str = typer.Option(
        ..., "--domain", help="Domain to host, e.g. example.com (a registered domain, no https://)"
    ),
) -> None:
    """Create a new DNS zone."""
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        result = client.create_dns_zone(Domain=domain)
        output_result(result, columns=_ZONE_COLUMNS, json_mode=state.json_output)


@dns_zone_app.command("delete")
def delete_zone(
    ctx: typer.Context,
    id: int = typer.Argument(..., help="DNS zone ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a DNS zone (prompts for confirmation)."""
    _state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        zone = client.get_dns_zone(id)
        domain = zone.get("Domain", "")
        if not yes:
            typer.confirm(f"Delete DNS zone {id} ({domain})?", abort=True)
        client.delete_dns_zone(id)
        typer.echo(f"Deleted DNS zone {id} ({domain}).")


@record_app.command(
    "add",
    epilog=examples(
        "bunnycdn dns-zone record add 42 --type A --name www \\",
        "  --value 203.0.113.10",
        "bunnycdn dns-zone record add 42 --type AAAA --name www \\",
        "  --value 2001:db8::10 --ttl 3600",
        "bunnycdn dns-zone record add 42 --type TXT --name @ \\",
        "  --value 'v=spf1 include:_spf.example.com ~all'",
        "bunnycdn dns-zone record add 42 --type MX --name @ \\",
        "  --value mail.example.com --priority 10",
        "bunnycdn dns-zone record add 42 --type SRV --name _sip._tcp \\",
        "  --value sip.example.com --priority 10 --weight 5 --port 5060",
    ),
)
def add_record(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="DNS zone ID"),
    type_: str = typer.Option(
        ..., "--type", help=f"Record type, case-insensitive: {', '.join(_RECORD_TYPES)}"
    ),
    name: str = typer.Option(
        ..., "--name", help="Record name relative to the zone: www, mail, or @ for the zone root"
    ),
    value: str = typer.Option(
        ...,
        "--value",
        help=(
            "Record value: an IPv4 address for A, IPv6 for AAAA (both checked); "
            "a hostname for CNAME/MX; text for TXT"
        ),
    ),
    ttl: int = typer.Option(300, "--ttl", help="TTL in seconds"),
    priority: int | None = typer.Option(
        None, "--priority", min=0, help="Priority; required for MX and SRV, rejected otherwise"
    ),
    weight: int | None = typer.Option(
        None, "--weight", min=0, help="Weight; required for SRV, rejected otherwise"
    ),
    port: int | None = typer.Option(
        None, "--port", min=0, help="Port; required for SRV, rejected otherwise"
    ),
) -> None:
    """Add a DNS record to a zone.

    A and AAAA values must be valid IPv4 and IPv6 addresses. MX records
    need --priority; SRV records need --priority, --weight and --port.
    """
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        record_type = _record_type(type_)
        value = _record_value(record_type, value)
        body = AddDnsRecordModel(Type=record_type, Name=name, Value=value, Ttl=ttl)
        _check_srv_fields(record_type, Priority=priority, Weight=weight, Port=port)
        if priority is not None:
            body["Priority"] = priority
        if weight is not None:
            body["Weight"] = weight
        if port is not None:
            body["Port"] = port
        result = client.add_dns_record(zone_id, **body)
        output_result(result, columns=_RECORD_COLUMNS, json_mode=state.json_output)


@record_app.command(
    "list",
    epilog=examples(
        "bunnycdn dns-zone record list 42",
        "bunnycdn --output-format json dns-zone record list 42",
    ),
)
def list_records(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="DNS zone ID"),
) -> None:
    """List a zone's DNS records, sorted by type then name.

    Use the Id column with `record update` and `record delete`. The name
    @ is the zone root.
    """
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        records = client.get_dns_zone(zone_id).get("Records") or []
        if state.json_output:
            output_result(records, json_mode=True)
            return
        rows = [
            {
                **r,
                "Type": _type_name(r.get("Type")),
                "Name": r.get("Name") or "@",
            }
            for r in records
        ]
        rows.sort(key=lambda r: (str(r["Type"]), r["Name"]))
        output_result(rows, columns=_LIST_COLUMNS)


@record_app.command(
    "update",
    epilog=examples(
        "bunnycdn dns-zone record update 42 7 --set Value=203.0.113.20",
        "bunnycdn dns-zone record update 42 7 --set Ttl=3600 --set Disabled=true",
        "bunnycdn dns-zone record update 42 7 --set Priority=10",
        "bunnycdn dns-zone record update 42 7 --set Type=AAAA \\",
        "  --set Value=2001:db8::10",
    ),
)
def update_record(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="DNS zone ID"),
    record_id: int = typer.Argument(..., help="DNS record ID (the Id column of `record list`)"),
    set_: list[str] = typer.Option([], "--set", help=SET_HELP),
) -> None:
    """Update a DNS record using --set KEY=VALUE.

    Type accepts a name (A, MX, ...) or its number. A new Value for an A
    or AAAA record is checked to be an IPv4 or IPv6 address.
    """
    state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        updates = parse_set_pairs(set_)  # ValueError is caught by sdk_errors
        # D-12: fetch zone to get the record's before state
        zone_before = client.get_dns_zone(zone_id)
        records_before = zone_before.get("Records") or []
        before_record = next((r for r in records_before if r.get("Id") == record_id), {})
        if isinstance(updates.get("Type"), str):  # a name like "A"; ints pass through
            updates["Type"] = _record_type(updates["Type"], hint="--set Type")
        record_type = updates.get("Type", before_record.get("Type"))
        value = updates.get("Value", before_record.get("Value"))
        changing = "Type" in updates or "Value" in updates
        if changing and isinstance(record_type, int) and value is not None:
            checked = _record_value(record_type, str(value), hint="--set Value")
            if "Value" in updates:
                updates["Value"] = checked
        # Apply update
        after = client.update_dns_record(zone_id, record_id, **updates)
        # D-15: json mode outputs updated resource
        if state.json_output:
            output_result(after, json_mode=True)
            return
        # D-13, D-14: diff table with only changed rows in red italic
        changed_keys = [
            k for k in updates if str(before_record.get(k, "")) != str(after.get(k, ""))
        ]
        if not changed_keys:
            typer.echo("No fields changed.")
            return
        table = Table("Field", "Before", "After")
        for k in changed_keys:
            table.add_row(
                k,
                Text(str(before_record.get(k, "")), style="bold red italic"),
                Text(str(after.get(k, "")), style="bold red italic"),
            )
        console.print(table)


@record_app.command("delete")
def delete_record(
    ctx: typer.Context,
    zone_id: int = typer.Argument(..., help="DNS zone ID"),
    record_id: int = typer.Argument(..., help="DNS record ID (the Id column of `record list`)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a DNS record (prompts for confirmation)."""
    _state, client = api_client(ctx, core.CoreClient)
    with sdk_errors():
        if not yes:
            typer.confirm(f"Delete DNS record {record_id} in zone {zone_id}?", abort=True)
        client.delete_dns_record(zone_id, record_id)
        typer.echo(f"Deleted DNS record {record_id} in zone {zone_id}.")
