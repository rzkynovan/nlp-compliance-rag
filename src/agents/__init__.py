"""
Multi-Agent System for NLP Compliance Auditor

This package implements a multi-agent architecture for regulatory compliance auditing:
- BaseAgent: Abstract base class for allspecialist agents
- BISpecialistAgent: Specialist for Bank Indonesia regulations
- OJKSpecialistAgent: Specialist for OJK regulations
- ConflictResolverAgent: Resolves conflicts between regulators
- CoordinatorAgent: Orchestrates multi-agent workflow
"""

from .base_agent import BaseAgent, AgentVerdict
from .bi_specialist import BISpecialistAgent
from .ojk_specialist import OJKSpecialistAgent
from .conflict_resolver import ConflictResolverAgent, FinalVerdict
from .coordinator import CoordinatorAgent

__all__ = [
    "BaseAgent",
    "AgentVerdict",
    "BISpecialistAgent",
    "OJKSpecialistAgent",
    "ConflictResolverAgent",
    "FinalVerdict",
    "CoordinatorAgent",
]