---
id: "0003"
title: "AI Employee Comprehensive Data Models"
stage: "spec"
date: "2026-02-21"
surface: "agent"
model: "claude-opus-4-6"
feature: "001-ai-employee"
branch: "001-silver-tier-ai"
user: "user"
command: "Based on the AI Employee specification and research findings, create comprehensive data models for: 1. Core entities: ActionItem, Invoice, Payment, SocialPost, BrandMention, HealthStatus 2. Entity relationships and constraints 3. State transitions where applicable 4. Data validation rules from requirements 5. JSON schemas for API contracts"
labels: ["data-model", "architecture", "specification"]
links:
  spec: "null"
  ticket: "null"
  adr: "null"
  pr: "null"
files:
  - "specs/001-ai-employee/spec.md"
  - "specs/001-ai-employee/research.md"
  - "specs/001-ai-employee/data-model.md (created)"
tests:
  - "none"
---

## Prompt

Based on the AI Employee specification and research findings, create comprehensive data models for:

1. Core entities: ActionItem, Invoice, Payment, SocialPost, BrandMention, HealthStatus
2. Entity relationships and constraints
3. State transitions where applicable
4. Data validation rules from requirements
5. JSON schemas for API contracts

Focus on small business scale (1-10 employees, <100 transactions/month) and ensure models support the specified workflows.

## Response snapshot

Created comprehensive data models at specs/001-ai-employee/data-model.md including:

1. **Core Entities Defined:**
   - ActionItem: Full TypeScript interface with states, priorities, source types, metadata
   - Invoice: Complete financial document model with line items, Odoo integration fields, approval workflow
   - Payment: Transaction model with reconciliation, approval thresholds, counterparty info
   - SocialPost: Multi-platform content model with scheduling, engagement metrics
   - BrandMention: Social monitoring model with sentiment analysis, alert system
   - HealthStatus: System monitoring model with components, resources, watchers, error tracking

2. **Entity Relationships:** Cardinalities documented with ASCII diagram showing 1:N and 1:1 relationships

3. **State Transitions:** State machines documented for ActionItem and Invoice with all valid transitions

4. **Validation Rules:**
   - Financial thresholds (FR-004): >$100 requires approval
   - Timing requirements from Success Criteria
   - Content limits per platform

5. **JSON Schemas:** Complete JSON Schema (Draft 7) for all 6 entities with all required properties, formats, and constraints

6. **File Storage Conventions:** Mapping of entities to Obsidian vault folder structure

7. **Scale Considerations:** Volume estimates and data retention policies for small business

## Outcome

- ✅ Impact: Created comprehensive data models supporting all AI Employee workflows
- 🧪 Tests: none
- 📁 Files: specs/001-ai-employee/data-model.md
- 🔁 Next prompts: Implement data validation layer, Create API endpoints, Build entity storage utilities
- 🧠 Reflection: The data models capture all functional requirements from spec.md including FR-001 through FR-015, and align with the approval workflow patterns established in research.md

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): none
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): none
