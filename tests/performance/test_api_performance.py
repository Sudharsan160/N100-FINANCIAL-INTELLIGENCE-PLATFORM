import concurrent.futures
import time

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_screener_10_concurrent_requests_under_10_seconds():
    def make_request():
        start = time.perf_counter()

        response = client.get(
            "/api/v1/screener",
            params={
                "min_roe": 10,
                "max_de": 2,
            },
        )

        elapsed = time.perf_counter() - start

        assert response.status_code == 200

        return elapsed

    start = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(
            executor.map(
                lambda _: make_request(),
                range(10),
            )
        )

    total_elapsed = time.perf_counter() - start

    assert len(results) == 10
    assert total_elapsed < 10.0


def test_company_profiles_under_3_seconds():
    tickers = [
        "TCS",
        "INFY",
        "RELIANCE",
        "HDFCBANK",
        "ITC",
    ]

    timings = []

    for ticker in tickers:
        start = time.perf_counter()

        response = client.get(f"/api/v1/companies/{ticker}")

        elapsed = time.perf_counter() - start
        timings.append(elapsed)

        assert response.status_code == 200

    assert len(timings) == 5
    assert all(elapsed < 3.0 for elapsed in timings)


def test_health_endpoint_performance():
    start = time.perf_counter()

    response = client.get("/api/v1/health")

    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 3.0
