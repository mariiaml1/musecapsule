from unittest.mock import Mock

from fastapi.testclient import TestClient

from musecapsule import server


def test_server_reuses_embedder_for_reference_uploads(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSECAPSULE_DEVKIT_DIR", str(tmp_path))
    monkeypatch.setenv(
        "MUSECAPSULE_DATABASE",
        str(tmp_path / "sessions.db"),
    )
    monkeypatch.setenv("MUSECAPSULE_RAG_ENABLED", "1")

    embed = Mock(
        side_effect=lambda texts: [[1.0] * 384 for _ in texts],
    )
    create_embedder = Mock(return_value=embed)
    graph = Mock()

    monkeypatch.setattr(server, "create_local_embedder", create_embedder)
    monkeypatch.setattr(
        server,
        "build_exploration_graph",
        Mock(return_value=graph),
    )

    app = server.create_local_app()

    with TestClient(app) as client:
        response = client.post(
            "/sessions",
            json={"goal": "Build an AI portfolio project"},
        )
        assert response.status_code == 201
        session = response.json()

        for text in [
            "Use bounded retries.",
            "Store session snapshots.",
        ]:
            response = client.post(
                f"/sessions/{session['id']}/references",
                json={"title": "Technical notes", "text": text},
            )
            assert response.status_code == 201
            assert response.json()["text"] == text

        assert client.get(
            f"/sessions/{session['id']}"
        ).json() == session

    create_embedder.assert_called_once_with()
    assert embed.call_count == 2
    graph.invoke.assert_not_called()


def test_server_skips_embedder_when_rag_is_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSECAPSULE_DEVKIT_DIR", str(tmp_path))
    monkeypatch.setenv(
        "MUSECAPSULE_DATABASE",
        str(tmp_path / "sessions.db"),
    )
    monkeypatch.delenv("MUSECAPSULE_RAG_ENABLED", raising=False)

    create_embedder = Mock()
    monkeypatch.setattr(server, "create_local_embedder", create_embedder)
    monkeypatch.setattr(server, "build_exploration_graph", Mock())

    app = server.create_local_app()

    with TestClient(app) as client:
        session = client.post(
            "/sessions",
            json={"goal": "Build an AI portfolio project"},
        ).json()

        response = client.post(
            f"/sessions/{session['id']}/references",
            json={"title": "Notes", "text": "Use bounded retries."},
        )

        search_response = client.post(
            f"/sessions/{session['id']}/references/search",
            json={"query": "Retries"},
        )
        assert search_response.status_code == 503

    assert response.status_code == 503
    create_embedder.assert_not_called()


def test_server_searches_saved_index_with_shared_embedder(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("MUSECAPSULE_DEVKIT_DIR", str(tmp_path))
    monkeypatch.setenv(
        "MUSECAPSULE_DATABASE",
        str(tmp_path / "sessions.db"),
    )
    monkeypatch.setenv("MUSECAPSULE_RAG_ENABLED", "1")

    embed = Mock(
        side_effect=lambda texts: [
            [1.0] + [0.0] * 383
            for _ in texts
        ],
    )
    create_embedder = Mock(return_value=embed)
    graph = Mock()

    monkeypatch.setattr(server, "create_local_embedder", create_embedder)
    monkeypatch.setattr(
        server,
        "build_exploration_graph",
        Mock(return_value=graph),
    )

    app = server.create_local_app()

    with TestClient(app) as client:
        session_ids = []

        for _ in range(2):
            response = client.post(
                "/sessions",
                json={"goal": "Build an AI portfolio project"},
            )
            assert response.status_code == 201
            session_ids.append(response.json()["id"])

        documents = []

        for session_id in session_ids:
            response = client.post(
                f"/sessions/{session_id}/references",
                json={
                    "title": "Reliability",
                    "text": "Use bounded retries.",
                },
            )
            assert response.status_code == 201
            documents.append(response.json())

        # Separate ingestion calls from the following search call.
        embed.reset_mock()

        query = "Repeat a failed request."
        response = client.post(
            f"/sessions/{session_ids[0]}/references/search",
            json={
                "query": query,
                "limit": 3,
                "min_score": 0.30,
            },
        )

        assert response.status_code == 200
        results = response.json()

        assert len(results) == 1
        assert results[0]["chunk"]["document_id"] == documents[0]["id"]
        assert results[0]["chunk"]["session_id"] == session_ids[0]
        assert results[0]["chunk"]["text"] == "Use bounded retries."

    create_embedder.assert_called_once_with()
    embed.assert_called_once_with([query])
    graph.invoke.assert_not_called()
