"""Test KP registry."""
from fastapi.testclient import TestClient

from kp_registry.server import app
from kp_registry.routers.kps import example

client = TestClient(app)


def test_main():
    """Test KP registry."""
    # clear all KPs
    response = client.post('/clear')
    assert response.status_code == 204

    # add KP
    response = client.post('/kps', json=example)
    assert response.status_code == 201

    # get KP
    response = client.get(f'/kps/{list(example)[0]}')
    assert response.status_code == 200

    # try to add KP again (you cannot)
    response = client.post('/kps', json=example)
    assert response.status_code == 400

    # get all KPs (there is one)
    response = client.get('/kps')
    assert response.status_code == 200
    assert len(response.json()) == 1

    # search for KPs (find none)
    response = client.post('/search', json=dict(
        source_type=['biolink:Disease'],
        edge_type=['-biolink:association->'],
        target_type=['biolink:Gene'],
    ))
    assert response.status_code == 200
    assert not response.json()

    # search for KPs (find one)
    response = client.post('/search', json=dict(
        source_type=['biolink:Disease'],
        edge_type=['-biolink:related_to->'],
        target_type=['biolink:Gene'],
    ))
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Check that the response includes operations
    assert len(response.json()['my_kp']['operations']) == 1

    # delete KP
    response = client.delete(f'/kps/{list(example)[0]}')
    assert response.status_code == 204
