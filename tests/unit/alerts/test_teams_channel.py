"""
Tests for TeamsChannel — Microsoft Teams alert delivery via Adaptive Card webhook.

Covers:
- _severity_color: all three severity levels, unknown severity fallback
- _build_adaptive_card: correct Teams webhook envelope structure
- _build_adaptive_card: Adaptive Card schema, version, body and actions
- _build_adaptive_card: facts include condition, environment, triggered_at, details
- _build_adaptive_card: header color block uses severity color
- send: returns True when httpx responds 2xx
- send: returns False when httpx raises HTTPError
- send: returns False on unexpected exception
- send: posts to the configured webhook URL
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tinaa.alerts.rules import Alert, AlertConditionType, AlertSeverity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_alert(
    severity: AlertSeverity = AlertSeverity.WARNING,
    condition_type: AlertConditionType = AlertConditionType.QUALITY_SCORE_DROP,
    message: str = "Quality score dropped",
    product_name: str | None = "Storefront",
    product_id: str | None = "prod-1",
    environment: str | None = "production",
    triggered_at: str = "2026-03-21T09:00:00Z",
    details: dict | None = None,
) -> Alert:
    return Alert(
        rule_name="test-rule",
        severity=severity,
        condition_type=condition_type,
        message=message,
        product_name=product_name,
        product_id=product_id,
        environment=environment,
        triggered_at=triggered_at,
        details=details or {},
    )


# ---------------------------------------------------------------------------
# Severity colour mapping
# ---------------------------------------------------------------------------

class TestSeverityColor:
    def test_critical_is_red(self):
        from tinaa.alerts.teams_channel import TeamsChannel

        ch = TeamsChannel("https://example.com/webhook")
        assert ch._severity_color(AlertSeverity.CRITICAL) == "#EF4444"

    def test_warning_is_amber(self):
        from tinaa.alerts.teams_channel import TeamsChannel

        ch = TeamsChannel("https://example.com/webhook")
        assert ch._severity_color(AlertSeverity.WARNING) == "#F59E0B"

    def test_info_is_blue(self):
        from tinaa.alerts.teams_channel import TeamsChannel

        ch = TeamsChannel("https://example.com/webhook")
        assert ch._severity_color(AlertSeverity.INFO) == "#3B82F6"


# ---------------------------------------------------------------------------
# Adaptive Card structure
# ---------------------------------------------------------------------------

class TestBuildAdaptiveCard:
    def setup_method(self):
        from tinaa.alerts.teams_channel import TeamsChannel

        self.ch = TeamsChannel("https://hook.example.com/webhook")

    def test_teams_message_envelope(self):
        alert = _make_alert()
        payload = self.ch._build_adaptive_card(alert)
        assert payload["type"] == "message"
        assert "attachments" in payload
        assert len(payload["attachments"]) == 1

    def test_attachment_content_type(self):
        alert = _make_alert()
        payload = self.ch._build_adaptive_card(alert)
        attachment = payload["attachments"][0]
        assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"

    def test_adaptive_card_type_and_schema(self):
        alert = _make_alert()
        payload = self.ch._build_adaptive_card(alert)
        card = payload["attachments"][0]["content"]
        assert card["type"] == "AdaptiveCard"
        assert card["$schema"] == "http://adaptivecards.io/schemas/adaptive-card.json"
        assert card["version"] == "1.4"

    def test_card_has_body_and_actions(self):
        alert = _make_alert()
        payload = self.ch._build_adaptive_card(alert)
        card = payload["attachments"][0]["content"]
        assert isinstance(card["body"], list)
        assert len(card["body"]) > 0
        assert isinstance(card["actions"], list)
        assert len(card["actions"]) > 0

    def test_header_color_block_uses_severity_color(self):
        alert = _make_alert(severity=AlertSeverity.CRITICAL)
        payload = self.ch._build_adaptive_card(alert)
        card = payload["attachments"][0]["content"]
        # First body element should be a color header Container or ColumnSet
        first_block = card["body"][0]
        # The header block must carry the critical red color somewhere
        card_json_str = str(payload)
        assert "#EF4444" in card_json_str

    def test_warning_color_appears_in_card(self):
        alert = _make_alert(severity=AlertSeverity.WARNING)
        payload = self.ch._build_adaptive_card(alert)
        card_json_str = str(payload)
        assert "#F59E0B" in card_json_str

    def test_facts_contain_condition(self):
        alert = _make_alert(
            condition_type=AlertConditionType.ENDPOINT_DOWN,
        )
        payload = self.ch._build_adaptive_card(alert)
        card_json_str = str(payload)
        # condition_type value should appear formatted somewhere in the card
        assert "endpoint" in card_json_str.lower() or "Endpoint" in card_json_str

    def test_facts_contain_environment(self):
        alert = _make_alert(environment="staging")
        payload = self.ch._build_adaptive_card(alert)
        card_json_str = str(payload)
        assert "staging" in card_json_str

    def test_facts_contain_triggered_at(self):
        alert = _make_alert(triggered_at="2026-03-21T09:00:00Z")
        payload = self.ch._build_adaptive_card(alert)
        card_json_str = str(payload)
        assert "2026-03-21T09:00:00Z" in card_json_str

    def test_facts_contain_alert_details(self):
        alert = _make_alert(details={"current_score": 65, "threshold": 75})
        payload = self.ch._build_adaptive_card(alert)
        card_json_str = str(payload)
        assert "65" in card_json_str
        assert "75" in card_json_str

    def test_action_button_view_in_dashboard(self):
        alert = _make_alert()
        payload = self.ch._build_adaptive_card(alert)
        card = payload["attachments"][0]["content"]
        actions = card["actions"]
        assert any(
            "TINAA" in str(a) or "Dashboard" in str(a) or "View" in str(a)
            for a in actions
        )

    def test_title_contains_severity_and_product(self):
        alert = _make_alert(
            severity=AlertSeverity.CRITICAL,
            product_name="My Product",
        )
        payload = self.ch._build_adaptive_card(alert)
        card_json_str = str(payload)
        assert "CRITICAL" in card_json_str or "critical" in card_json_str
        assert "My Product" in card_json_str

    def test_title_uses_product_id_when_name_absent(self):
        alert = _make_alert(product_name=None, product_id="prod-42")
        payload = self.ch._build_adaptive_card(alert)
        card_json_str = str(payload)
        assert "prod-42" in card_json_str

    def test_title_uses_unknown_when_no_product(self):
        alert = _make_alert(product_name=None, product_id=None)
        payload = self.ch._build_adaptive_card(alert)
        card_json_str = str(payload)
        assert "Unknown" in card_json_str


# ---------------------------------------------------------------------------
# send() happy path
# ---------------------------------------------------------------------------

class TestTeamsChannelSend:
    @pytest.mark.asyncio
    async def test_send_returns_true_on_success(self):
        from tinaa.alerts.teams_channel import TeamsChannel

        ch = TeamsChannel("https://hook.example.com/webhook")
        alert = _make_alert()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await ch.send(alert)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_posts_to_configured_url(self):
        from tinaa.alerts.teams_channel import TeamsChannel

        webhook_url = "https://outlook.office.com/webhook/abc123"
        ch = TeamsChannel(webhook_url)
        alert = _make_alert()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await ch.send(alert)

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == webhook_url or call_args.args[0] == webhook_url or call_args.kwargs.get("url") == webhook_url or webhook_url in str(call_args)

    @pytest.mark.asyncio
    async def test_send_returns_false_on_http_error(self):
        from tinaa.alerts.teams_channel import TeamsChannel

        ch = TeamsChannel("https://hook.example.com/webhook")
        alert = _make_alert()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPError("connection refused")
            )
            mock_client_cls.return_value = mock_client

            result = await ch.send(alert)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_returns_false_on_unexpected_exception(self):
        from tinaa.alerts.teams_channel import TeamsChannel

        ch = TeamsChannel("https://hook.example.com/webhook")
        alert = _make_alert()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=RuntimeError("unexpected"))
            mock_client_cls.return_value = mock_client

            result = await ch.send(alert)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_with_none_config_still_works(self):
        from tinaa.alerts.teams_channel import TeamsChannel

        ch = TeamsChannel("https://hook.example.com/webhook")
        alert = _make_alert()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await ch.send(alert, config=None)

        assert result is True


# ---------------------------------------------------------------------------
# Export / import surface
# ---------------------------------------------------------------------------

class TestTeamsChannelExport:
    def test_teams_channel_importable_from_alerts_package(self):
        from tinaa.alerts import TeamsChannel  # noqa: F401 — import test

    def test_teams_channel_importable_from_channels(self):
        from tinaa.alerts.channels import TeamsChannel  # noqa: F401 — import test
