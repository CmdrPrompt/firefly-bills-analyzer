"""EXAMPLE - remove this file once real step definitions exist.

Demonstrates pytest-bdd scenario binding and the step registration/reuse
convention: steps live in tests/bdd/steps/, and existing steps should be
searched before new ones are written so wording stays reusable across
feature files.
"""

from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/example_search.feature")


@given(parsers.parse('a catalog containing "{item}"'), target_fixture="catalog")
def catalog_with_item(item):
    return {item}


@when(parsers.parse('I search for "{item}"'))
def search_for_item(catalog, item):
    catalog.add(f"searched:{item}")


@then(parsers.parse('I should see "{item}" in the results'))
def item_in_results(catalog, item):
    assert item in catalog
