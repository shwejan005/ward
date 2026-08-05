"""Core module — zero external dependencies (ADR-002).

This module defines abstract interfaces and shared exception types.
Every other backend module may depend on core; core depends on nothing.
"""
