from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["db_row_counts"]["companies"] == 92


def test_list_companies_returns_92_companies():
    response = client.get("/api/v1/companies")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 92
    assert len(data["companies"]) == 92


def test_company_profile_tcs():
    response = client.get("/api/v1/companies/TCS")

    assert response.status_code == 200

    data = response.json()

    assert data["company"]["id"] == "TCS"
    assert data["company"]["company_name"]
    assert "sector" in data
    assert "latest_kpis" in data


def test_company_profit_and_loss_tcs():
    response = client.get(
        "/api/v1/companies/TCS/pl",
        params={
            "from_year": "2020-01",
            "to_year": "2024-12",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] >= 5
    assert len(data["data"]) >= 5


def test_company_ratios_tcs():
    response = client.get(
        "/api/v1/companies/TCS/ratios",
        params={"year": 2024},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] >= 1
    assert data["data"]


def test_screener_returns_companies():
    response = client.get("/api/v1/screener")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 92
    assert len(data["data"]) == 92


def test_screener_with_quality_filters():
    response = client.get(
        "/api/v1/screener",
        params={
            "min_roe": 10,
            "max_de": 2,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert 0 <= data["count"] <= 92

    for company in data["data"]:
        if company.get("roe") is not None:
            assert company["roe"] >= 10

        # Financial companies are intentionally exempt from the
        # D/E ceiling because the screener applies the same
        # Financials carve-out used by the dashboard.
        if (
            company.get("debt_to_equity") is not None
            and (company.get("broad_sector") or "").strip().casefold() != "financials"
        ):
            assert company["debt_to_equity"] <= 2


def test_list_sectors():
    response = client.get("/api/v1/sectors")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 10
    assert len(data["sectors"]) == 10


def test_financials_sector_companies():
    response = client.get("/api/v1/sectors/Financials/companies")

    assert response.status_code == 200

    data = response.json()

    assert data["sector"] == "Financials"
    assert data["count"] == 23
    assert len(data["companies"]) == 23


def test_invalid_company_returns_404():
    response = client.get("/api/v1/companies/NOT_A_REAL_TICKER")

    assert response.status_code == 404
