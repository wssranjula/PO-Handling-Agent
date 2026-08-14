import base64

from app.services.gmail import (
    decode_base64url,
    gmail_provider_id,
    iter_message_parts,
    message_headers,
)


def test_decodes_gmail_base64url_without_padding() -> None:
    encoded = base64.urlsafe_b64encode(b"purchase order").decode().rstrip("=")
    assert decode_base64url(encoded) == b"purchase order"


def test_finds_nested_attachments() -> None:
    payload = {
        "parts": [
            {"mimeType": "text/plain", "body": {"data": "ignored"}},
            {
                "mimeType": "multipart/mixed",
                "parts": [
                    {
                        "filename": "order.pdf",
                        "mimeType": "application/pdf",
                        "body": {"attachmentId": "attachment-1"},
                    }
                ],
            },
        ]
    }
    parts = list(iter_message_parts(payload))
    assert [part["filename"] for part in parts] == ["order.pdf"]


def test_normalizes_message_header_names() -> None:
    payload = {
        "headers": [
            {"name": "From", "value": "Buyer <buyer@example.com>"},
            {"name": "Subject", "value": "PO attached"},
        ]
    }
    assert message_headers(payload) == {
        "from": "Buyer <buyer@example.com>",
        "subject": "PO attached",
    }


def test_provider_id_uses_short_mime_part_id() -> None:
    part = {"partId": "2.1", "body": {"attachmentId": "x" * 600}}
    assert gmail_provider_id("message-123", part) == "gmail:message-123:2.1"


def test_provider_id_hashes_attachment_when_part_id_is_missing() -> None:
    part = {"body": {"attachmentId": "x" * 600}}
    provider_id = gmail_provider_id("message-123", part)
    assert provider_id.startswith("gmail:message-123:")
    assert len(provider_id) < 255
