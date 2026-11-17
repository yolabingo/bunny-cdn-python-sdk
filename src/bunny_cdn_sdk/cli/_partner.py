"""Partner Portal CLI sub-app."""

from __future__ import annotations

import sys
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import typer

from bunny_cdn_sdk import partner
from bunny_cdn_sdk.cli._options import WHEN_FORMATS, examples, when
from bunny_cdn_sdk.cli._output import api_client, err_console, output_result, sdk_errors

if TYPE_CHECKING:
    from collections.abc import Callable

partner_app = typer.Typer(
    no_args_is_help=True,
    help="Partner Portal: customers, billing, pricing. Uses --partner-api-key.",
)
customer_app = typer.Typer(no_args_is_help=True, help="Partner customers.")
product_app = typer.Typer(no_args_is_help=True, help="Per-customer product access.")
partner_app.add_typer(customer_app, name="customer")
customer_app.add_typer(product_app, name="product")

_CUSTOMER_COLS = ["CustomerUserId", "Email", "CompanyName", "ContractBillingType", "ContractValue"]
_BILLING_COLS = ["Id", "Amount", "Type", "Timestamp", "InvoiceAvailable"]
_PRODUCT_COLS = ["ProductId", "IsEnabled", "ResourceCount"]
_AUDIT_COLS = ["Timestamp", "Product", "ResourceType", "ResourceId", "Action", "ActorId"]


class _Order(StrEnum):
    Ascending = "Ascending"
    Descending = "Descending"


# Spec's PartnerCustomerProductType, lowercased and without separators.
_PRODUCTS = {
    "cdn": 1,
    "database": 2,
    "bunnydb": 2,
    "dns": 3,
    "magiccontainers": 4,
    "optimizer": 5,
    "scripting": 6,
    "edgescripting": 6,
    "shield": 7,
    "storage": 8,
    "stream": 9,
}


_PRODUCT_HELP = (
    "Product name (cdn, database, dns, magic-containers, optimizer, scripting, shield, "
    "storage, stream; case and -/_ ignored) or number 1-9"
)


def _product_id(value: str) -> int:
    key = value.lower().replace("-", "").replace("_", "")
    pid = _PRODUCTS.get(key) or (int(key) if key.isdecimal() else 0)
    if pid not in _PRODUCTS.values():
        msg = f"unknown product '{value}' (use 1-9 or cdn, database, dns, magic-containers, ...)"
        raise typer.BadParameter(msg)
    return pid


def _run(
    ctx: typer.Context,
    call: Callable[[partner.PartnerClient], Any],
    columns: list[str] | None = None,
) -> None:
    """Run ``call(client)`` and print the result (JSON when no columns or a JSON output format)."""
    state, client = api_client(ctx, partner.PartnerClient, partner=True)
    with sdk_errors():
        output_result(call(client), columns=columns, json_mode=state.json_output or columns is None)


@partner_app.command("overview")
def overview(ctx: typer.Context) -> None:
    """Show the partner overview."""
    _run(ctx, lambda c: c.get_partner_overview())


@partner_app.command("contract")
def contract(ctx: typer.Context) -> None:
    """Show the partner contract."""
    _run(ctx, lambda c: c.get_contract())


@partner_app.command("pricing")
def pricing(ctx: typer.Context) -> None:
    """Show the partner pricing."""
    _run(ctx, lambda c: c.get_partner_pricing())


@customer_app.command("list")
def customer_list(ctx: typer.Context) -> None:
    """List customers."""
    _run(ctx, lambda c: c.list_customers(), _CUSTOMER_COLS)


@customer_app.command("get")
def customer_get(
    ctx: typer.Context, id: str = typer.Argument(..., help="Customer user ID")
) -> None:
    """Show a customer overview."""
    _run(ctx, lambda c: c.get_customer_overview(id))


@customer_app.command(
    "create",
    epilog=examples(
        "bunnycdn partner customer create jane@example.com",
        "bunnycdn partner customer create jane@example.com \\",
        "  --first-name Jane --last-name Doe --country US \\",
        "  --company-name 'Example Inc'",
    ),
)
def customer_create(
    ctx: typer.Context,
    email: str = typer.Argument(..., help="Email address of the new customer account"),
    first_name: str | None = typer.Option(None, "--first-name", help="Customer's first name"),
    last_name: str | None = typer.Option(None, "--last-name", help="Customer's last name"),
    country: str | None = typer.Option(
        None, "--country", help="Two-letter ISO country code, e.g. US, DE"
    ),
    billing_email: str | None = typer.Option(
        None, "--billing-email", help="Email for invoices, if different from the account email"
    ),
    company_name: str | None = typer.Option(
        None, "--company-name", help="Company name, e.g. 'Example Inc'"
    ),
    company_vat_number: str | None = typer.Option(
        None, "--company-vat-number", help="Company VAT number, e.g. DE123456789"
    ),
    internal_notes: str | None = typer.Option(
        None, "--internal-notes", help="Free-text note, visible to partners only"
    ),
) -> None:
    """Create a customer account."""
    fields = {
        "FirstName": first_name,
        "LastName": last_name,
        "Country": country,
        "BillingEmail": billing_email,
        "CompanyName": company_name,
        "CompanyVatNumber": company_vat_number,
        "InternalNotes": internal_notes,
    }
    _run(ctx, lambda c: c.create_customer(email, **{k: v for k, v in fields.items() if v}))


@customer_app.command("invite")
def customer_invite(
    ctx: typer.Context, email: str = typer.Argument(..., help="Email address to invite")
) -> None:
    """Invite a user to become a customer."""
    _run(ctx, lambda c: c.invite_customer(email))


@customer_app.command("billing")
def customer_billing(
    ctx: typer.Context, id: str = typer.Argument(..., help="Customer user ID")
) -> None:
    """List a customer's billing records."""
    state, client = api_client(ctx, partner.PartnerClient, partner=True)
    with sdk_errors():
        data = client.get_customer_billing(id)
        if state.json_output:
            output_result(data, json_mode=True)
        else:
            output_result(data.get("BillingRecords") or [], columns=_BILLING_COLS)


@customer_app.command(
    "invoice",
    epilog=examples(
        "bunnycdn partner customer invoice 4a1b2c 12345",
        "bunnycdn partner customer invoice 4a1b2c 12345 -o inv.pdf",
        "bunnycdn partner customer invoice 4a1b2c 12345 -o - > inv.pdf",
    ),
)
def customer_invoice(
    ctx: typer.Context,
    id: str = typer.Argument(..., help="Customer user ID"),
    billing_record_id: int = typer.Argument(
        ..., help="Billing record ID (the Id column of `customer billing`)"
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="File to write (default: invoice-<ID>.pdf); '-' writes the PDF to stdout",
    ),
) -> None:
    """Download an invoice PDF."""
    _state, client = api_client(ctx, partner.PartnerClient, partner=True)
    with sdk_errors():
        pdf = client.download_invoice_pdf(id, billing_record_id)
        path = output or f"invoice-{billing_record_id}.pdf"
        if path == "-":
            sys.stdout.buffer.write(pdf)
            sys.stdout.buffer.flush()
        else:
            with open(path, "wb") as f:  # noqa: PTH123
                f.write(pdf)
        err_console.print(
            f"Wrote invoice {billing_record_id} to {'stdout' if path == '-' else path}."
        )


@customer_app.command("pricing")
def customer_pricing(
    ctx: typer.Context, id: str = typer.Argument(..., help="Customer user ID")
) -> None:
    """Show a customer's pricing."""
    _run(ctx, lambda c: c.get_customer_pricing(id))


@customer_app.command(
    "audit",
    epilog=examples(
        "bunnycdn partner customer audit 4a1b2c",
        "bunnycdn partner customer audit 4a1b2c yesterday --all",
        "bunnycdn partner customer audit 4a1b2c 2026-10-15 \\",
        "  --resource-id 12345 --order Descending --limit 50",
    ),
)
def customer_audit(
    ctx: typer.Context,
    id: str = typer.Argument(..., help="Customer user ID"),
    date: str = typer.Argument("today", help=f"Day to show: {WHEN_FORMATS}"),
    product: list[str] = typer.Option(
        [], "--product", help="Only this product, as shown in the Product column (repeatable)"
    ),
    resource_type: list[str] = typer.Option(
        [],
        "--resource-type",
        help="Only this resource type, as shown in the ResourceType column (repeatable)",
    ),
    resource_id: list[str] = typer.Option(
        [], "--resource-id", help="Only this resource ID, e.g. a pull zone ID (repeatable)"
    ),
    actor_id: list[str] = typer.Option(
        [], "--actor-id", help="Only actions by this user ID (repeatable)"
    ),
    order: _Order | None = typer.Option(
        None, "--order", help="Sort by time; the API default applies if omitted"
    ),
    limit: int | None = typer.Option(
        None, "--limit", help="Maximum entries per page (default: the API's page size)"
    ),
    all_: bool = typer.Option(False, "--all", help="Follow continuation tokens through all pages"),
) -> None:
    """Show a customer's audit log (one page, or every page with --all).

    Shows one day. Repeat a filter to match any of several values;
    different filters combine.
    """
    state, client = api_client(ctx, partner.PartnerClient, partner=True)
    date = when(date, hint="DATE").date().isoformat()
    filters: dict[str, Any] = {
        "product": product or None,
        "resource_type": resource_type or None,
        "resource_id": resource_id or None,
        "actor_id": actor_id or None,
        "order": order.value if order else None,
        "limit": limit,
    }
    with sdk_errors():
        if all_:
            rows = list(client.iter_audit_log(id, date, **filters))
        else:
            page = client.get_audit_log(id, date, **filters)
            if state.json_output:
                output_result(page, json_mode=True)
                return
            rows = page.get("Logs") or []
            if page.get("HasMoreData"):
                err_console.print("More entries available; use --all.")
        output_result(rows, columns=_AUDIT_COLS, json_mode=state.json_output)


@product_app.command("list")
def product_list(
    ctx: typer.Context, id: str = typer.Argument(..., help="Customer user ID")
) -> None:
    """List a customer's products and whether each is enabled."""
    _run(ctx, lambda c: c.list_customer_products(id), _PRODUCT_COLS)


def _set_product(ctx: typer.Context, id: str, product: str, *, enabled: bool) -> None:
    pid = _product_id(product)
    _state, client = api_client(ctx, partner.PartnerClient, partner=True)
    with sdk_errors():
        client.set_customer_product(id, pid, enabled=enabled)
        typer.echo(f"{'Enabled' if enabled else 'Disabled'} product {pid} for {id}.")


@product_app.command(
    "enable",
    epilog=examples(
        "bunnycdn partner customer product enable 4a1b2c cdn",
        "bunnycdn partner customer product enable 4a1b2c magic-containers",
        "bunnycdn partner customer product enable 4a1b2c 8",
    ),
)
def product_enable(
    ctx: typer.Context,
    id: str = typer.Argument(..., help="Customer user ID"),
    product: str = typer.Argument(..., help=_PRODUCT_HELP),
) -> None:
    """Enable a product for a customer."""
    _set_product(ctx, id, product, enabled=True)


@product_app.command(
    "disable",
    epilog=examples(
        "bunnycdn partner customer product disable 4a1b2c dns",
        "bunnycdn partner customer product disable 4a1b2c 3",
    ),
)
def product_disable(
    ctx: typer.Context,
    id: str = typer.Argument(..., help="Customer user ID"),
    product: str = typer.Argument(..., help=_PRODUCT_HELP),
) -> None:
    """Disable a product for a customer."""
    _set_product(ctx, id, product, enabled=False)
