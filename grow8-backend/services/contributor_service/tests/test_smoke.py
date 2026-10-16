from app import main


def test_service_name() -> None:
    assert main.SERVICE_NAME == "contributor_service"
