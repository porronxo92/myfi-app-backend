"""
Tests de Seguridad - Validación de Propiedad
============================================

Tests para verificar que la validación de propiedad de recursos
funciona correctamente y protege contra acceso no autorizado.
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import MagicMock, patch

from app.services.chat_service import ChatService


class TestOwnershipValidation:
    """Tests para validación de propiedad de recursos en ChatService."""

    @pytest.fixture
    def mock_db(self):
        """Crea un mock de la sesión de base de datos."""
        return MagicMock()

    @pytest.fixture
    def user_id(self):
        """Genera un UUID de usuario para tests."""
        return uuid4()

    @pytest.fixture
    def chat_service(self, mock_db, user_id):
        """Crea una instancia de ChatService para testing."""
        return ChatService(mock_db, user_id)

    # ============================================
    # VALIDACIÓN DE TRANSACCIONES
    # ============================================

    def test_validate_transaction_ownership_valid(self, chat_service, mock_db, user_id):
        """Permite acceso a transacciones del propio usuario."""
        tx_id = str(uuid4())

        # Mock: la transacción existe y pertenece al usuario
        mock_tx = MagicMock()
        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = mock_tx

        result = chat_service._validate_transaction_ownership(tx_id)

        assert result is True

    def test_validate_transaction_ownership_not_found(self, chat_service, mock_db):
        """Rechaza transacciones que no existen."""
        tx_id = str(uuid4())

        # Mock: la transacción no existe
        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = None

        result = chat_service._validate_transaction_ownership(tx_id)

        assert result is False

    def test_validate_transaction_ownership_other_user(self, chat_service, mock_db):
        """Rechaza transacciones de otros usuarios."""
        tx_id = str(uuid4())

        # Mock: la transacción no pertenece al usuario (filtro retorna None)
        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = None

        result = chat_service._validate_transaction_ownership(tx_id)

        assert result is False

    def test_validate_transaction_ownership_invalid_uuid(self, chat_service):
        """Rechaza UUIDs inválidos."""
        invalid_ids = [
            "not-a-uuid",
            "12345",
            "",
            None,
            "00000000-0000-0000-0000-00000000000X",
        ]

        for invalid_id in invalid_ids:
            result = chat_service._validate_transaction_ownership(invalid_id)
            assert result is False, f"Debería rechazar UUID inválido: {invalid_id}"

    # ============================================
    # VALIDACIÓN DE CUENTAS
    # ============================================

    def test_validate_account_ownership_valid(self, chat_service, mock_db, user_id):
        """Permite acceso a cuentas del propio usuario."""
        account_id = str(uuid4())

        # Mock: la cuenta existe y pertenece al usuario
        mock_account = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_account

        result = chat_service._validate_account_ownership(account_id)

        assert result is True

    def test_validate_account_ownership_not_found(self, chat_service, mock_db):
        """Rechaza cuentas que no existen."""
        account_id = str(uuid4())

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = chat_service._validate_account_ownership(account_id)

        assert result is False

    def test_validate_account_ownership_invalid_uuid(self, chat_service):
        """Rechaza UUIDs de cuenta inválidos."""
        result = chat_service._validate_account_ownership("invalid-uuid")
        assert result is False

    # ============================================
    # VALIDACIÓN DE CATEGORÍAS
    # ============================================

    def test_validate_category_ownership_valid(self, chat_service, mock_db, user_id):
        """Permite acceso a categorías del propio usuario."""
        category_id = str(uuid4())

        # Mock: la categoría existe y pertenece al usuario
        mock_category = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_category

        result = chat_service._validate_category_ownership(category_id)

        assert result is True

    def test_validate_category_ownership_not_found(self, chat_service, mock_db):
        """Rechaza categorías que no existen."""
        category_id = str(uuid4())

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = chat_service._validate_category_ownership(category_id)

        assert result is False

    # ============================================
    # ESCAPE DE PATRONES SQL
    # ============================================

    def test_escape_like_pattern_basic(self, chat_service):
        """Escapa caracteres especiales de SQL LIKE."""
        test_cases = [
            ("normal", "normal"),
            ("100%", "100\\%"),
            ("_test", "\\_test"),
            ("a%b_c", "a\\%b\\_c"),
            ("\\", "\\\\"),
        ]

        for input_val, expected in test_cases:
            result = chat_service._escape_like_pattern(input_val)
            assert result == expected, f"Input '{input_val}' debería escaparse a '{expected}', pero fue '{result}'"

    def test_escape_like_pattern_empty(self, chat_service):
        """Maneja valores vacíos correctamente."""
        assert chat_service._escape_like_pattern("") == ""
        assert chat_service._escape_like_pattern(None) is None


class TestBuildersWithValidation:
    """Tests para builders que usan validación de propiedad."""

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.fixture
    def chat_service(self, mock_db, user_id):
        return ChatService(mock_db, user_id)

    def test_build_delete_transaction_validates_ownership(self, chat_service, mock_db):
        """_build_delete_transaction_action valida propiedad."""
        tx_id = str(uuid4())

        # Mock: la transacción NO pertenece al usuario
        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = None

        result = chat_service._build_delete_transaction_action(
            {"transaction_id": tx_id, "description_confirm": "Test"},
            {}
        )

        assert result is None  # Debería retornar None si no tiene permisos

    def test_build_update_transaction_validates_ownership(self, chat_service, mock_db):
        """_build_update_transaction_action valida propiedad."""
        tx_id = str(uuid4())

        # Mock: la transacción NO pertenece al usuario
        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = None

        result = chat_service._build_update_transaction_action(
            {"transaction_id": tx_id, "amount": 100},
            {}
        )

        assert result is None

    def test_build_delete_category_validates_existence(self, chat_service, mock_db):
        """_build_delete_category_action retorna None si categoría no existe."""
        # Mock: la categoría no existe
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = chat_service._build_delete_category_action(
            {"category_name": "NoExiste"},
            {}
        )

        assert result is None

    def test_build_update_account_validates_ownership(self, chat_service, mock_db):
        """_build_update_account_action valida propiedad."""
        # Mock: la cuenta no pertenece al usuario
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Mock _find_account para que no encuentre la cuenta
        chat_service._find_account = MagicMock(return_value=None)

        result = chat_service._build_update_account_action(
            {"account_name": "CuentaOtro", "new_name": "Hacked"},
            {}
        )

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
