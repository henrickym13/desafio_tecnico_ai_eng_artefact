from datetime import date, datetime

import pytest

from src.agent.tool_registry import ToolRegistry
from src.config import settings
from src.data.loader import load_dataset
from src.data.repositories import OrderRepository, ProductRepository
from src.policies.sectioner import load_sections
from src.services.memory import SessionState
from src.services.store_hours import TZ


@pytest.fixture(scope="session")
def ds():
    return load_dataset(settings.raw_data_dir)


@pytest.fixture(scope="session")
def products_repo(ds):
    return ProductRepository(ds)


@pytest.fixture(scope="session")
def orders_repo(ds):
    return OrderRepository(ds)


@pytest.fixture(scope="session")
def policy_sections():
    return load_sections(settings.policy_pdf)


@pytest.fixture
def session():
    return SessionState(session_id="test")


@pytest.fixture
def registry(products_repo, orders_repo, policy_sections):
    # "hoje" = sexta-feira 2026-02-20, 10:00 (pedido 7 está dentro do arrependimento)
    return ToolRegistry(
        products=products_repo, orders=orders_repo, policy_sections=policy_sections,
        today_fn=lambda: date(2026, 2, 20),
        now_fn=lambda: datetime(2026, 2, 20, 10, 0, tzinfo=TZ),
    )
