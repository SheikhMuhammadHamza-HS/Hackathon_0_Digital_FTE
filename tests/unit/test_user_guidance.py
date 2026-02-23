"""Unit tests for user guidance system."""

import pytest
from ai_employee.utils.user_guidance import (
    UserGuide,
    GuidanceCategory,
    get_help_for_error
)


class TestUserGuide:
    """Test UserGuide class."""

    def test_get_guidance_by_category(self):
        """Test getting guidance by category."""
        guide = UserGuide()

        guidance = guide.get_guidance(GuidanceCategory.GETTING_STARTED)

        assert "title" in guidance
        assert "Getting Started with AI Employee" in guidance["title"]
        assert "sections" in guidance

    def test_get_guidance_by_section(self):
        """Test getting specific section guidance."""
        guide = UserGuide()

        guidance = guide.get_guidance(
            GuidanceCategory.TROUBLESHOOTING,
            "common_issues"
        )

        assert isinstance(guidance, dict)
        # Should return the common_issues section

    def test_get_guidance_invalid_category(self):
        """Test getting guidance with invalid category."""
        guide = UserGuide()

        guidance = guide.get_guidance("invalid_category")

        assert "error" in guidance
        assert "invalid_category" in guidance["error"]

    def test_search_guidance(self):
        """Test searching guidance content."""
        guide = UserGuide()

        # Search for Odoo-related issues
        results = guide.search_guidance("odoo")

        assert isinstance(results, list)
        # Should find Odoo connection issues

    def test_search_guidance_no_results(self):
        """Test searching with no results."""
        guide = UserGuide()

        results = guide.search_guidance("xyz123nonexistent")

        assert results == []

    def test_get_contextual_help(self):
        """Test getting contextual help for endpoints."""
        guide = UserGuide()

        help_text = guide.get_contextual_help("/api/v1/health")

        assert "description" in help_text
        assert "health" in help_text["description"].lower() or "status" in help_text["description"].lower()

    def test_get_contextual_help_unknown_endpoint(self):
        """Test getting help for unknown endpoint."""
        guide = UserGuide()

        help_text = guide.get_contextual_help("/api/v1/unknown")

        assert "description" in help_text
        assert "No specific help" in help_text["description"]

    def test_generate_setup_checklist(self):
        """Test setup checklist generation."""
        guide = UserGuide()

        checklist = guide.generate_setup_checklist()

        assert "title" in checklist
        assert "sections" in checklist
        assert len(checklist["sections"]) > 0

        # Check specific sections exist
        section_names = [s["name"] for s in checklist["sections"]]
        assert "Prerequisites" in section_names
        assert "Configuration" in section_names
        assert "Directory Structure" in section_names
        assert "Service Verification" in section_names


class TestGetHelpForError:
    """Test get_help_for_error function."""

    def test_configuration_error_help(self):
        """Test help for configuration errors."""
        help_text = get_help_for_error("Missing API_KEY in configuration")

        assert help_text["category"] == "configuration"
        assert ".env file" in help_text["suggestions"][0]
        assert "environment variables" in help_text["suggestions"][1]

    def test_authentication_error_help(self):
        """Test help for authentication errors."""
        help_text = get_help_for_error("401 Unauthorized: Invalid token")

        assert help_text["category"] == "authentication"
        assert any("API tokens" in s for s in help_text["suggestions"])

    def test_network_error_help(self):
        """Test help for network errors."""
        help_text = get_help_for_error("Connection timeout")

        assert help_text["category"] == "network"
        assert "internet connectivity" in help_text["suggestions"][0]

    def test_permission_error_help(self):
        """Test help for permission errors."""
        help_text = get_help_for_error("Permission denied")

        assert help_text["category"] == "permissions"
        assert "file/directory permissions" in help_text["suggestions"][0]

    def test_general_error_help(self):
        """Test help for unrecognized errors."""
        help_text = get_help_for_error("Some unknown error occurred")

        assert help_text["category"] == "general"
        assert len(help_text["suggestions"]) >= 3


class TestGuidanceCategory:
    """Test GuidanceCategory enum."""

    def test_all_categories_exist(self):
        """Test all expected categories exist."""
        expected_categories = {
            "getting_started",
            "troubleshooting",
            "best_practices",
            "faq",
            "error_resolution"
        }

        actual_categories = {cat.value for cat in GuidanceCategory}
        assert actual_categories == expected_categories

    def test_category_creation(self):
        """Test category creation from string."""
        category = GuidanceCategory("troubleshooting")
        assert category == GuidanceCategory.TROUBLESHOOTING

    def test_invalid_category(self):
        """Test invalid category raises error."""
        with pytest.raises(ValueError):
            GuidanceCategory("invalid_category")