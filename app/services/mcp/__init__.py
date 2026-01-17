"""
MCP (Model Context Protocol) Layer
===================================

Este módulo implementa la capa MCP que actúa como puente inteligente entre
Gemini AI y la base de datos PostgreSQL, proporcionando funciones estructuradas
que Gemini puede invocar para obtener información financiera contextual.
"""

from .financial_context import MCPFinancialContext

__all__ = ['MCPFinancialContext']
