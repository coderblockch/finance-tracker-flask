def _add_category(client, name="Trabajo"):
    return client.post("/categories", data={"name": name}, follow_redirects=True)


def test_add_transaction(client, auth):
    auth.register()
    auth.login()
    _add_category(client)

    response = client.post(
        "/transactions",
        data={
            "title": "Salario",
            "amount": "1000",
            "category_id": "1",
            "movement_type": "Ingreso",
            "occurred_on": "2026-11-01",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Salario" in response.data
    assert b"1000.00" in response.data
    assert b"Income" in response.data


def test_add_expense_is_stored_negative(client, auth):
    auth.register()
    auth.login()
    _add_category(client, "Comida")

    response = client.post(
        "/transactions",
        data={
            "title": "Comida",
            "amount": "20",
            "category_id": "1",
            "movement_type": "Gasto",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Comida" in response.data
    assert b"-20.00" in response.data


def test_add_transaction_requires_login(client):
    response = client.post(
        "/transactions",
        data={
            "title": "Salario",
            "amount": "1000",
            "category_id": "1",
            "movement_type": "Ingreso",
        },
    )
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_add_transaction_requires_category(client, auth):
    auth.register()
    auth.login()
    response = client.post(
        "/transactions",
        data={
            "title": "Salario",
            "amount": "1000",
            "category_id": "1",
            "movement_type": "Ingreso",
        },
        follow_redirects=True,
    )
    assert b"Add a category before recording a transaction." in response.data
