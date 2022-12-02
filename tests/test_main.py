"""Test KP registry."""
import httpx
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
                "x-trapi": {"version": "1.3.0", "operations": ["lookup"]},
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
                "x-trapi": {"version": "1.3.0", "operations": ["lookup"]},
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
    await registry.refresh()

    # get all KPs (there is one)
    kp = registry.get_one("Test KP")
    assert kp is not None

    # # search for KPs (find one)
    response = registry.search(
        subject_category=["biolink:ChemicalSubstance"],
        predicate=["biolink:treats"],
        object_category=["biolink:Disease"],
        maturity=["development"],
    )
    print(response)
    assert len(response) == 1


example_kp = {
    "my_kp": {
        "url": "http://my_kp_url",
        "infores": "infores:my_kp",
        "maturity": "development",
        "operations": [
            {
                "subject_category": "biolink:Disease",
                "predicate": "biolink:related_to",
                "object_category": "biolink:Gene",
            }
        ],
    }
}


@pytest.mark.asyncio
async def test_add(httpx_mock):
    """Test manual KP registry."""
    # httpx_mock.add_response(json=smart_api_response)
    # httpx_mock.add_response(json=test_kp_response)
    # httpx_mock.add_response(json=test_kp_2_response)
    registry = Registry()
    # clear all KPs
    registry.clear()

    # add KP
    registry.add(**example_kp)

    # get KP
    kp = registry.get_one("my_kp")
    assert kp is not None

    # try to add KP again (you cannot)
    registry.add(**example_kp)

    # get all KPs (there is one)
    kps = registry.get_all()
    assert len(kps) == 1

    # search for KPs (find none)
    kp = registry.search(
        subject_category=["biolink:Disease"],
        predicate=["-biolink:association->"],
        object_category=["biolink:Gene"],
        maturity=["development"],
    )
    assert not kp

    # search for KPs (find one)
    kp = registry.search(
        subject_category=["biolink:Disease"],
        predicate=["biolink:related_to"],
        object_category=["biolink:Gene"],
        maturity=["development"],
    )
    assert len(kp) == 1

    # Check that the response includes operations
    assert len(kp["my_kp"]["operations"]) == 1
