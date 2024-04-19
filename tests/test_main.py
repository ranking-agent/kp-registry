"""Test KP registry."""
import pytest

from kp_registry.main import Registry


smart_api_response = {
    "hits": [
        {
            "_id": "123abc",
            "servers": [
                {
                    "url": "http://test-kp",
                    "x-maturity": "development",
                }
            ],
            "info": {
                "title": "Test KP",
                "x-translator": {"component": "KP"},
                "x-trapi": {"version": "1.5.0", "operations": ["lookup"]},
            },
            "paths": {"/meta_knowledge_graph": {}},
        },
        {
            "_id": "456def",
            "servers": [
                {
                    "url": "http://test-kp-2",
                    "x-maturity": "development",
                }
            ],
            "info": {
                "title": "Test KP 2",
                "x-translator": {"component": "KP"},
                "x-trapi": {"version": "1.5.0", "operations": ["lookup"]},
            },
            "paths": {"/meta_knowledge_graph": {}},
        },
    ]
}

test_kp_response = {
    "nodes": {
        "biolink:ChemicalSubstance": {"id_prefixes": ["CHEBI", "PUBCHEM.COMPOUND"]}
    },
    "edges": [
        {
            "subject": "biolink:ChemicalSubstance",
            "predicate": "biolink:treats",
            "object": "biolink:Disease",
        }
    ],
}

test_kp_2_response = {
    "nodes": {
        "biolink:ChemicalSubstance": {"id_prefixes": ["CHEBI", "PUBCHEM.COMPOUND"]}
    },
    "edges": [
        {
            "subject": "biolink:Gene",
            "predicate": "biolink:correlated_with",
            "object": "biolink:Disease",
        }
    ],
}


@pytest.mark.asyncio
async def test_main(httpx_mock):
    """Test KP registry."""
    httpx_mock.add_response(json=smart_api_response)
    httpx_mock.add_response(json=test_kp_response)
    httpx_mock.add_response(json=test_kp_2_response)
    registry = Registry()
    # refresh KPs
    kps = await registry.retrieve_kps()

    assert len(kps) == 2

    assert kps["Test KP 2"]["infores"] == "infores:456def"

    assert (
        kps["Test KP"]["details"]["preferred_prefixes"]["biolink:ChemicalSubstance"]
        == test_kp_response["nodes"]["biolink:ChemicalSubstance"]["id_prefixes"]
    )
