"""Tests for partner CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from bunny_cdn_sdk._exceptions import BunnyAuthenticationError
from bunny_cdn_sdk.cli import app

ROW = {
    "CustomerUserId": "needle",
    "Id": 7,
    "Email": "needle",
    "ProductId": "needle",
    "Timestamp": "needle",
    "Product": "needle",
}

# (args, client method, expected positional args, return value)
CASES = [
    ("overview", "get_partner_overview", [], ROW),
    ("contract", "get_contract", [], ROW),
    ("pricing", "get_partner_pricing", [], ROW),
    ("customer list", "list_customers", [], [ROW]),
    ("customer get u1", "get_customer_overview", ["u1"], ROW),
    ("customer create a@b.c", "create_customer", ["a@b.c"], ROW),
    ("customer invite a@b.c", "invite_customer", ["a@b.c"], ROW),
    ("customer billing u1", "get_customer_billing", ["u1"], {"BillingRecords": [ROW]}),
    ("customer pricing u1", "get_customer_pricing", ["u1"], ROW),
    ("customer audit u1 2026-01-31", "get_audit_log", ["u1", "2026-01-31"], {"Logs": [ROW]}),
    ("customer product list u1", "list_customer_products", ["u1"], [ROW]),
    ("customer product enable u1 cdn", "set_customer_product", ["u1", 1], None),
    ("customer product disable u1 stream", "set_customer_product", ["u1", 9], None),
    ("customer invoice u1 7 -o -", "download_invoice_pdf", ["u1", 7], b"%PDF"),
]


def _exc() -> BunnyAuthenticationError:
    return BunnyAuthenticationError(status_code=401, message="err", response=MagicMock())


def _invoke(runner, args: str, *, global_args: tuple[str, ...] = ("--api-key", "k")):
    return runner.invoke(app, [*global_args, "partner", *args.split()])


@pytest.mark.parametrize(("args", "method", "pos", "ret"), CASES)
def test_success(runner, args, method, pos, ret) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        c = M.return_value
        getattr(c, method).return_value = ret
        result = _invoke(runner, args)
    assert result.exit_code == 0, result.output
    assert M.call_args.kwargs == {"api_key": "k"}
    assert getattr(c, method).call_args.args == tuple(pos)
    if ret is not None and not isinstance(ret, bytes):
        assert "needle" in result.output


@pytest.mark.parametrize(("args", "method", "pos", "ret"), CASES)
def test_error(runner, args, method, pos, ret) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        getattr(M.return_value, method).side_effect = _exc()
        assert _invoke(runner, args).exit_code == 1


@pytest.mark.parametrize(("args", "method", "pos", "ret"), CASES)
def test_missing_auth(runner, args, method, pos, ret) -> None:
    result = _invoke(runner, args, global_args=())
    assert result.exit_code == 1
    assert "BUNNY_PARTNER_API_KEY" in result.output
    assert "BUNNY_API_KEY" in result.output


def test_partner_key_wins(runner) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        M.return_value.get_contract.return_value = ROW
        result = _invoke(
            runner, "contract", global_args=("--api-key", "a", "--partner-api-key", "p")
        )
    assert result.exit_code == 0
    assert M.call_args.kwargs == {"api_key": "p"}


def test_falls_back_to_api_key(runner) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        M.return_value.get_contract.return_value = ROW
        assert _invoke(runner, "contract", global_args=("--api-key", "a")).exit_code == 0
    assert M.call_args.kwargs == {"api_key": "a"}


def test_partner_key_from_env(runner) -> None:
    runner.env["BUNNY_PARTNER_API_KEY"] = "envp"
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        M.return_value.get_contract.return_value = ROW
        assert _invoke(runner, "contract", global_args=()).exit_code == 0
    assert M.call_args.kwargs == {"api_key": "envp"}


def test_json(runner) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        M.return_value.list_customers.return_value = [ROW]
        result = runner.invoke(
            app, ["--api-key", "k", "--output-format", "json", "partner", "customer", "list"]
        )
    assert result.exit_code == 0
    assert json.loads(result.output) == [ROW]


def test_create_options(runner) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        c = M.return_value
        c.create_customer.return_value = ROW
        result = _invoke(
            runner,
            "customer create a@b.c --first-name Ann --last-name Lee --country DE "
            "--billing-email b@b.c --company-name Co --company-vat-number V1 --internal-notes n",
        )
    assert result.exit_code == 0, result.output
    assert c.create_customer.call_args.kwargs == {
        "FirstName": "Ann",
        "LastName": "Lee",
        "Country": "DE",
        "BillingEmail": "b@b.c",
        "CompanyName": "Co",
        "CompanyVatNumber": "V1",
        "InternalNotes": "n",
    }


def test_invoice_default_path(runner, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        M.return_value.download_invoice_pdf.return_value = b"%PDF-1"
        result = _invoke(runner, "customer invoice u1 7")
    assert result.exit_code == 0, result.output
    assert (tmp_path / "invoice-7.pdf").read_bytes() == b"%PDF-1"
    assert "Wrote invoice" in result.output  # confirmation goes to stderr


def test_invoice_explicit_path(runner, tmp_path) -> None:
    out = tmp_path / "x.pdf"
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        M.return_value.download_invoice_pdf.return_value = b"%PDF-2"
        result = _invoke(runner, f"customer invoice u1 7 --output {out}")
    assert result.exit_code == 0, result.output
    assert out.read_bytes() == b"%PDF-2"


def test_invoice_stdout(runner, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        M.return_value.download_invoice_pdf.return_value = b"%PDF-3"
        result = _invoke(runner, "customer invoice u1 7 -o -")
    assert result.exit_code == 0, result.output
    assert result.stdout_bytes.startswith(b"%PDF-3")
    assert not list(tmp_path.iterdir())


def test_audit_filters_single_page(runner) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        c = M.return_value
        c.get_audit_log.return_value = {"Logs": [ROW], "HasMoreData": True}
        result = _invoke(
            runner,
            "customer audit u1 2026-01-31 --product Cdn --product Dns --resource-type t "
            "--resource-id r --actor-id a --order Descending --limit 5",
        )
    assert result.exit_code == 0, result.output
    assert c.get_audit_log.call_args.kwargs == {
        "product": ["Cdn", "Dns"],
        "resource_type": ["t"],
        "resource_id": ["r"],
        "actor_id": ["a"],
        "order": "Descending",
        "limit": 5,
    }
    c.iter_audit_log.assert_not_called()
    assert "--all" in result.output


def test_audit_all_uses_iterator(runner) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        c = M.return_value
        c.iter_audit_log.return_value = iter([ROW, ROW])
        result = _invoke(runner, "customer audit u1 2026-01-31 --all --order Ascending")
    assert result.exit_code == 0, result.output
    assert c.iter_audit_log.call_args.args == ("u1", "2026-01-31")
    assert c.iter_audit_log.call_args.kwargs["order"] == "Ascending"
    c.get_audit_log.assert_not_called()


def test_audit_bad_order(runner) -> None:
    assert _invoke(runner, "customer audit u1 2026-01-31 --order Sideways").exit_code == 2


@pytest.mark.parametrize(
    ("name", "pid"),
    [
        ("CDN", 1),
        ("Database", 2),
        ("dns", 3),
        ("magic-containers", 4),
        ("Optimizer", 5),
        ("scripting", 6),
        ("edge-scripting", 6),
        ("bunny-db", 2),
        ("shield", 7),
        ("storage", 8),
        ("stream", 9),
        ("5", 5),
    ],
)
def test_product_names_and_ids(runner, name, pid) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        result = _invoke(runner, f"customer product enable u1 {name}")
    assert result.exit_code == 0, result.output
    assert M.return_value.set_customer_product.call_args.args == ("u1", pid)
    assert M.return_value.set_customer_product.call_args.kwargs == {"enabled": True}


def test_product_disable_sets_false(runner) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        _invoke(runner, "customer product disable u1 cdn")
    assert M.return_value.set_customer_product.call_args.kwargs == {"enabled": False}


@pytest.mark.parametrize("bad", ["nope", "0", "10"])
def test_product_invalid(runner, bad) -> None:
    with patch("bunny_cdn_sdk.partner.PartnerClient") as M:
        result = _invoke(runner, f"customer product enable u1 {bad}")
    assert result.exit_code == 2
    M.return_value.set_customer_product.assert_not_called()
