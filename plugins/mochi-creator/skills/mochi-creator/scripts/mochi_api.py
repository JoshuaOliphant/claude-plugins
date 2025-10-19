#!/usr/bin/env python3
"""
ABOUTME: Mochi API client for creating and managing flashcards, decks, and templates.
ABOUTME: Provides a Python interface to the Mochi.cards REST API with authentication and error handling.

Dependencies: requests
Install with: pip install requests
"""

import os
import sys
import json
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlencode
import requests
from requests.auth import HTTPBasicAuth


class MochiAPIError(Exception):
    """Custom exception for Mochi API errors."""
    pass


class MochiAPI:
    """Client for interacting with the Mochi.cards API."""

    BASE_URL = "https://app.mochi.cards/api/"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Mochi API client.

        Args:
            api_key: Mochi API key. If not provided, reads from MOCHI_API_KEY environment variable.

        Raises:
            MochiAPIError: If no API key is provided or found in environment.
        """
        self.api_key = api_key or os.getenv("MOCHI_API_KEY")
        if not self.api_key:
            raise MochiAPIError(
                "No API key provided. Set MOCHI_API_KEY environment variable or pass api_key parameter."
            )
        self.auth = HTTPBasicAuth(self.api_key, "")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        """
        Make a request to the Mochi API.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters

        Returns:
            Response data as dict or None for DELETE requests

        Raises:
            MochiAPIError: If the request fails
        """
        url = urljoin(self.BASE_URL, endpoint.lstrip("/"))

        try:
            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30
            )

            if response.status_code == 204:
                return None

            if not response.ok:
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    pass

                error_msg = f"API request failed with status {response.status_code}"
                if "errors" in error_data:
                    error_msg += f": {error_data['errors']}"
                raise MochiAPIError(error_msg)

            if response.text:
                return response.json()
            return None

        except requests.RequestException as e:
            raise MochiAPIError(f"Network error: {str(e)}")

    # Card operations

    def create_card(
        self,
        content: str,
        deck_id: str,
        template_id: Optional[str] = None,
        fields: Optional[Dict[str, Dict[str, str]]] = None,
        archived: bool = False,
        review_reverse: bool = False,
        pos: Optional[str] = None,
        manual_tags: Optional[List[str]] = None
    ) -> Dict:
        """
        Create a new card.

        Args:
            content: Markdown content of the card
            deck_id: ID of the deck to add the card to
            template_id: Optional template ID to use
            fields: Optional dict of field IDs to field values
            archived: Whether the card is archived
            review_reverse: Whether to review in reverse order
            pos: Relative position within deck (lexicographic sorting)
            manual_tags: List of tags (without # prefix)

        Returns:
            Created card data

        Example:
            >>> api = MochiAPI()
            >>> card = api.create_card(
            ...     content="# What is Python?\\n---\\nA high-level programming language",
            ...     deck_id="abc123",
            ...     manual_tags=["programming", "python"]
            ... )
        """
        data = {
            "content": content,
            "deck-id": deck_id,
            "archived?": archived,
            "review-reverse?": review_reverse
        }

        if template_id:
            data["template-id"] = template_id
        if fields:
            data["fields"] = fields
        if pos:
            data["pos"] = pos
        if manual_tags:
            data["manual-tags"] = manual_tags

        return self._request("POST", "/cards/", data=data)

    def get_card(self, card_id: str) -> Dict:
        """
        Retrieve a card by ID.

        Args:
            card_id: The card ID

        Returns:
            Card data
        """
        return self._request("GET", f"/cards/{card_id}")

    def list_cards(
        self,
        deck_id: Optional[str] = None,
        limit: int = 10,
        bookmark: Optional[str] = None
    ) -> Dict:
        """
        List cards with optional filtering and pagination.

        Args:
            deck_id: Optional deck ID to filter by
            limit: Number of cards per page (1-100, default 10)
            bookmark: Pagination cursor from previous request

        Returns:
            Dict with 'docs' (list of cards) and 'bookmark' (for next page)
        """
        params = {"limit": limit}
        if deck_id:
            params["deck-id"] = deck_id
        if bookmark:
            params["bookmark"] = bookmark

        return self._request("GET", "/cards/", params=params)

    def update_card(
        self,
        card_id: str,
        content: Optional[str] = None,
        deck_id: Optional[str] = None,
        template_id: Optional[str] = None,
        fields: Optional[Dict[str, Dict[str, str]]] = None,
        archived: Optional[bool] = None,
        trashed: Optional[str] = None,
        review_reverse: Optional[bool] = None,
        pos: Optional[str] = None,
        manual_tags: Optional[List[str]] = None
    ) -> Dict:
        """
        Update an existing card.

        Args:
            card_id: The card ID to update
            content: New markdown content
            deck_id: Move to different deck
            template_id: Change template
            fields: Update field values
            archived: Archive/unarchive
            trashed: ISO 8601 timestamp to trash, or None to untrash
            review_reverse: Update reverse review setting
            pos: Update position
            manual_tags: Update tags (replaces existing)

        Returns:
            Updated card data
        """
        data = {}
        if content is not None:
            data["content"] = content
        if deck_id is not None:
            data["deck-id"] = deck_id
        if template_id is not None:
            data["template-id"] = template_id
        if fields is not None:
            data["fields"] = fields
        if archived is not None:
            data["archived?"] = archived
        if trashed is not None:
            data["trashed?"] = trashed
        if review_reverse is not None:
            data["review-reverse?"] = review_reverse
        if pos is not None:
            data["pos"] = pos
        if manual_tags is not None:
            data["manual-tags"] = manual_tags

        return self._request("POST", f"/cards/{card_id}", data=data)

    def delete_card(self, card_id: str) -> None:
        """
        Permanently delete a card.

        Warning: This cannot be undone. Consider using update_card with trashed parameter for soft delete.

        Args:
            card_id: The card ID to delete
        """
        self._request("DELETE", f"/cards/{card_id}")

    # Deck operations

    def create_deck(
        self,
        name: str,
        parent_id: Optional[str] = None,
        sort: Optional[int] = None,
        archived: bool = False,
        sort_by: str = "none",
        cards_view: str = "list",
        show_sides: bool = True,
        sort_by_direction: bool = False,
        review_reverse: bool = False
    ) -> Dict:
        """
        Create a new deck.

        Args:
            name: Deck name
            parent_id: Optional parent deck ID for nesting
            sort: Numeric sort order
            archived: Whether deck is archived
            sort_by: How to sort cards (none, lexicographically, created-at, updated-at, etc.)
            cards_view: Display mode (list, grid, note, column)
            show_sides: Show all sides of cards
            sort_by_direction: Reverse sort order
            review_reverse: Review cards in reverse

        Returns:
            Created deck data
        """
        data = {
            "name": name,
            "archived?": archived,
            "sort-by": sort_by,
            "cards-view": cards_view,
            "show-sides?": show_sides,
            "sort-by-direction": sort_by_direction,
            "review-reverse?": review_reverse
        }

        if parent_id:
            data["parent-id"] = parent_id
        if sort is not None:
            data["sort"] = sort

        return self._request("POST", "/decks/", data=data)

    def get_deck(self, deck_id: str) -> Dict:
        """
        Retrieve a deck by ID.

        Args:
            deck_id: The deck ID

        Returns:
            Deck data
        """
        return self._request("GET", f"/decks/{deck_id}")

    def list_decks(self, bookmark: Optional[str] = None) -> Dict:
        """
        List all decks with pagination.

        Args:
            bookmark: Pagination cursor from previous request

        Returns:
            Dict with 'docs' (list of decks) and 'bookmark' (for next page)
        """
        params = {}
        if bookmark:
            params["bookmark"] = bookmark

        return self._request("GET", "/decks/", params=params)

    def update_deck(
        self,
        deck_id: str,
        name: Optional[str] = None,
        parent_id: Optional[str] = None,
        sort: Optional[int] = None,
        archived: Optional[bool] = None,
        trashed: Optional[str] = None,
        sort_by: Optional[str] = None,
        cards_view: Optional[str] = None,
        show_sides: Optional[bool] = None,
        sort_by_direction: Optional[bool] = None,
        review_reverse: Optional[bool] = None
    ) -> Dict:
        """
        Update an existing deck.

        Args:
            deck_id: The deck ID to update
            name: New name
            parent_id: Move to different parent
            sort: Update sort order
            archived: Archive/unarchive
            trashed: ISO 8601 timestamp to trash, or None to untrash
            sort_by: Update sort method
            cards_view: Update view mode
            show_sides: Update show sides setting
            sort_by_direction: Update sort direction
            review_reverse: Update reverse review setting

        Returns:
            Updated deck data
        """
        data = {}
        if name is not None:
            data["name"] = name
        if parent_id is not None:
            data["parent-id"] = parent_id
        if sort is not None:
            data["sort"] = sort
        if archived is not None:
            data["archived?"] = archived
        if trashed is not None:
            data["trashed?"] = trashed
        if sort_by is not None:
            data["sort-by"] = sort_by
        if cards_view is not None:
            data["cards-view"] = cards_view
        if show_sides is not None:
            data["show-sides?"] = show_sides
        if sort_by_direction is not None:
            data["sort-by-direction"] = sort_by_direction
        if review_reverse is not None:
            data["review-reverse?"] = review_reverse

        return self._request("POST", f"/decks/{deck_id}", data=data)

    def delete_deck(self, deck_id: str) -> None:
        """
        Permanently delete a deck.

        Warning: This cannot be undone. Cards and child decks are NOT deleted.
        Consider using update_deck with trashed parameter for soft delete.

        Args:
            deck_id: The deck ID to delete
        """
        self._request("DELETE", f"/decks/{deck_id}")

    # Template operations

    def create_template(
        self,
        name: str,
        content: str,
        fields: Dict[str, Dict[str, Any]],
        pos: Optional[str] = None,
        style: Optional[Dict[str, str]] = None,
        options: Optional[Dict[str, bool]] = None
    ) -> Dict:
        """
        Create a new template.

        Args:
            name: Template name
            content: Markdown content with field placeholders like << Field name >>
            fields: Dict of field definitions
            pos: Position for sorting
            style: Style options (e.g., text-alignment)
            options: Template options (e.g., show-sides-separately?)

        Returns:
            Created template data

        Example:
            >>> fields = {
            ...     "front": {
            ...         "id": "front",
            ...         "name": "Front",
            ...         "type": "text",
            ...         "pos": "a"
            ...     },
            ...     "back": {
            ...         "id": "back",
            ...         "name": "Back",
            ...         "type": "text",
            ...         "pos": "b",
            ...         "options": {"multi-line?": True}
            ...     }
            ... }
            >>> template = api.create_template(
            ...     name="Basic Flashcard",
            ...     content="# << Front >>\\n---\\n<< Back >>",
            ...     fields=fields
            ... )
        """
        data = {
            "name": name,
            "content": content,
            "fields": fields
        }

        if pos:
            data["pos"] = pos
        if style:
            data["style"] = style
        if options:
            data["options"] = options

        return self._request("POST", "/templates/", data=data)

    def get_template(self, template_id: str) -> Dict:
        """
        Retrieve a template by ID.

        Args:
            template_id: The template ID

        Returns:
            Template data
        """
        return self._request("GET", f"/templates/{template_id}")

    def list_templates(self, bookmark: Optional[str] = None) -> Dict:
        """
        List all templates with pagination.

        Args:
            bookmark: Pagination cursor from previous request

        Returns:
            Dict with 'docs' (list of templates) and 'bookmark' (for next page)
        """
        params = {}
        if bookmark:
            params["bookmark"] = bookmark

        return self._request("GET", "/templates/", params=params)


def main():
    """CLI interface for testing the Mochi API."""
    if len(sys.argv) < 2:
        print("Usage: python mochi_api.py <command> [args...]")
        print("\nCommands:")
        print("  list-decks              - List all decks")
        print("  list-cards <deck-id>    - List cards in a deck")
        print("  create-deck <name>      - Create a new deck")
        print("  create-card <deck-id> <content> - Create a card")
        sys.exit(1)

    try:
        api = MochiAPI()
        command = sys.argv[1]

        if command == "list-decks":
            result = api.list_decks()
            print(json.dumps(result, indent=2))

        elif command == "list-cards":
            if len(sys.argv) < 3:
                print("Error: deck-id required")
                sys.exit(1)
            result = api.list_cards(deck_id=sys.argv[2])
            print(json.dumps(result, indent=2))

        elif command == "create-deck":
            if len(sys.argv) < 3:
                print("Error: deck name required")
                sys.exit(1)
            result = api.create_deck(name=sys.argv[2])
            print(json.dumps(result, indent=2))

        elif command == "create-card":
            if len(sys.argv) < 4:
                print("Error: deck-id and content required")
                sys.exit(1)
            result = api.create_card(deck_id=sys.argv[2], content=sys.argv[3])
            print(json.dumps(result, indent=2))

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except MochiAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
