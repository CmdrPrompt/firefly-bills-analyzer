# EXAMPLE — remove this file once real scenarios exist.
# Demonstrates the declarative Given/When/Then style expected of BDD
# acceptance criteria: describe what the user achieves, not UI mechanics.
Feature: Example search
  As a user
  I want to search a catalog for an item
  So that I can find what I am looking for

  Scenario: Finding an existing item
    Given a catalog containing "widget"
    When I search for "widget"
    Then I should see "widget" in the results
