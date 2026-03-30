"""
Tests for email delivery infrastructure and API response helpers.
EmailDeliveryLog and EmailRetryQueue models are planned for a future sprint.
"""
import pytest


@pytest.mark.skip(reason="EmailDeliveryLog model not yet implemented")
class TestEmailDeliveryLog:
    pass


@pytest.mark.skip(reason="EmailRetryQueue model not yet implemented")
class TestEmailRetryQueue:
    pass


@pytest.mark.django_db
class TestAPIResponse:
    def test_success_response_format(self):
        from invoices.api.response import APIResponse
        response = APIResponse.success(data={"test": "data"}, message="OK")
        assert response.data["success"] is True
        assert response.data["data"]["test"] == "data"

    def test_error_response_format(self):
        from invoices.api.response import APIResponse
        response = APIResponse.error(code="ERR", message="Something went wrong")
        assert response.data["success"] is False
        assert response.data["error"]["code"] == "ERR"
