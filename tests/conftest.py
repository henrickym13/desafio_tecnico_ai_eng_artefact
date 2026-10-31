from datetime import date

import pytest

from src.agent.tool_registry import ToolRegistry
from src.config import settings
from src.data.loader import load_dataset
from src.data.repositories import OrderRepository, ProductRepository
from src.services.memory import SessionState


@pytest.fixture(scope="session")
def ds():
    return load_dataset(settings.raw_data_dir)


@pytest.fixture(scope="session")
def products_repo(ds):
    return ProductRepository(ds)


@pytest.fixture(scope="session")
def orders_repo(ds):
    return OrderRepository(ds)


@pytest.fixture
def session():
    return SessionState(session_id="test")


@pytest.fixture
def registry(products_repo, orders_repo):
    return ToolRegistry(products=products_repo, orders=orders_repo, today_fn=lambda: date(2026, 2, 20))
