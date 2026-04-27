# Skill Scheduling & Auto-Dispatch

Complete guide for automatic skill discovery, planning, and execution in autonomous mode.

## Overview

The autonomous-builder skill can automatically:
1. Read `Claude_Skills_中文指南.md` from workspace root
2. Analyze task requirements and identify needed skills
3. Plan which skills to use for each feature/task
4. Auto-dispatch skills during execution without user intervention

## Skill Discovery Protocol

### Step 1: Load Skills Guide

```markdown
ON PROJECT INITIALIZATION:

1. Check for Claude_Skills_中文指南.md in workspace root:
   - Path: {{PROJECT_DIR}}/Claude_Skills_中文指南.md

2. If found:
   - Read and parse the guide
   - Build internal skill catalog
   - Match task types to available skills

3. If not found:
   - Continue with built-in skill knowledge
   - Log warning: "Skills guide not found, using default mappings"
```

### Step 2: Skill Matching Algorithm

```python
def match_skills_to_task(task_description: str, task_category: str, skills_guide: dict) -> List[SkillRecommendation]:
    """Match task requirements to available skills."""

    recommendations = []

    # Category-based matching
    category_skills = {
        "code_review": ["code-reviewer", "code-review-excellence"],
        "data_analysis": ["exploratory-data-analysis", "statistical-analysis"],
        "data_visualization": ["data-artist", "matplotlib", "plotly"],
        "ml_training": ["senior-ml-engineer", "pytorch-lightning", "scikit-learn"],
        "ml_evaluation": ["evaluating-machine-learning-models", "shap"],
        "scientific_writing": ["scientific-writing", "scientific-schematics"],
        "documentation": ["docs-write", "writing-docs"],
        "debugging": ["debugging-strategies", "error-resolver"],
        "architecture": ["architecture-patterns"],
        "bioinformatics": ["biopython", "bioservices", "gget"],
        "drug_discovery": ["torchdrug", "rdkit", "uniprot-database"],
        "protein_analysis": ["uniprot-database", "alphafold-database"],
        "testing": ["property-based-testing", "performance-testing"],
    }

    # Keyword matching from guide
    keywords = extract_keywords(task_description)

    for skill_name, skill_info in skills_guide.items():
        score = calculate_relevance_score(task_description, keywords, skill_info)
        if score > THRESHOLD:
            recommendations.append(SkillRecommendation(
                skill=skill_name,
                confidence=score,
                reason=f"Matched keywords: {matched_keywords}"
            ))

    return sorted(recommendations, key=lambda x: x.confidence, reverse=True)
```

## Task-Skill Mapping Reference

### By Task Category

| Task Category | Recommended Skills | Priority |
|--------------|-------------------|----------|
| **代码审查** | code-reviewer, code-review-excellence | High |
| **数据分析** | exploratory-data-analysis, statistical-analysis | High |
| **数据可视化** | data-artist, matplotlib, plotly, seaborn | High |
| **机器学习训练** | senior-ml-engineer, pytorch-lightning, scikit-learn | High |
| **模型评估** | evaluating-machine-learning-models, shap | High |
| **科学写作** | scientific-writing, scientific-schematics | Medium |
| **文档编写** | docs-write, writing-docs, documentation-lookup | Medium |
| **调试排错** | debugging-strategies, error-resolver | High |
| **架构设计** | architecture-patterns | High |
| **测试编写** | property-based-testing, performance-testing | Medium |
| **生物信息学** | biopython, bioservices, gget | Domain-specific |
| **药物发现** | torchdrug, rdkit, uniprot-database | Domain-specific |
| **蛋白质分析** | uniprot-database, alphafold-database | Domain-specific |

### By Feature Type

```json
{
  "feature_skill_mapping": {
    "api_development": ["architecture-patterns", "code-reviewer"],
    "database_design": ["architecture-patterns"],
    "frontend_ui": ["code-reviewer", "testing"],
    "data_pipeline": ["exploratory-data-analysis", "data-quality-frameworks"],
    "ml_model": ["senior-ml-engineer", "pytorch-lightning", "evaluating-machine-learning-models"],
    "visualization": ["data-artist", "matplotlib", "plotly"],
    "documentation": ["docs-write", "writing-docs"],
    "testing": ["property-based-testing", "performance-testing"],
    "optimization": ["performance-testing", "debugging-strategies"],
    "security": ["code-reviewer"]
  }
}
```

## Skill Dispatch Protocol

### Automatic Skill Invocation

```markdown
DURING FEATURE IMPLEMENTATION:

1. Before starting a task step:
   - Identify task type from step description
   - Look up recommended skills from planning phase
   - Check if skill is available

2. Invoke skill automatically:
   ```
   Using Skill tool to invoke: {skill_name}
   Reason: {matched_reason}
   ```

3. Skill execution:
   - Skill provides specialized guidance
   - Continue with skill's recommendations
   - Log skill usage to state

4. After skill completion:
   - Return to main workflow
   - Continue with next step
```

### Skill Dispatch Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SKILL DISPATCH WORKFLOW                       │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │  Task Step      │
                    │  Description    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Parse Task     │
                    │  Type & Keywords│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Query Skills   │
                    │  Guide/Catalog  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
     ┌─────────────────┐           ┌─────────────────┐
     │ Match Found?    │──NO──────▶│ Use Built-in    │
     └────────┬────────┘           │ Knowledge       │
              │YES                 └─────────────────┘
              ▼
     ┌─────────────────┐
     │ Auto-invoke     │
     │ Skill tool      │
     │                 │
     │ Skill: {name}   │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │ Execute with    │
     │ Skill Guidance  │
     └────────┬────────┘
              │
              ▼
     ┌─────────────────┐
     │ Log Usage to    │
     │ state.json      │
     └─────────────────┘
```

## Skill Planning Integration

### Feature Planning with Skills

When creating features.json, each feature includes recommended skills:

```json
{
  "features": [
    {
      "id": "feat-001",
      "name": "Data Analysis Module",
      "description": "Analyze dataset and create visualizations",
      "status": "pending",

      "recommended_skills": [
        {
          "skill": "exploratory-data-analysis",
          "phase": "implementation",
          "reason": "Required for initial data exploration"
        },
        {
          "skill": "data-artist",
          "phase": "implementation",
          "reason": "Required for publication-quality visualizations"
        },
        {
          "skill": "statistical-analysis",
          "phase": "implementation",
          "reason": "Required for statistical tests"
        }
      ],

      "skill_dispatch_schedule": [
        {
          "step": 1,
          "action": "Load and explore data",
          "invoke_skill": "exploratory-data-analysis"
        },
        {
          "step": 2,
          "action": "Perform statistical tests",
          "invoke_skill": "statistical-analysis"
        },
        {
          "step": 3,
          "action": "Create visualizations",
          "invoke_skill": "data-artist"
        }
      ]
    }
  ]
}
```

### State Tracking for Skills

```json
{
  "skill_dispatch": {
    "guide_loaded": true,
    "guide_path": "Claude_Skills_中文指南.md",
    "guide_version": "2.0",

    "skills_invoked": [
      {
        "skill": "exploratory-data-analysis",
        "invoked_at": "2026-02-13T10:30:00Z",
        "feature": "feat-001",
        "step": 1,
        "outcome": "success"
      },
      {
        "skill": "data-artist",
        "invoked_at": "2026-02-13T11:15:00Z",
        "feature": "feat-001",
        "step": 3,
        "outcome": "success"
      }
    ],

    "available_skills": [
      "code-reviewer", "data-artist", "debugging-strategies",
      "scientific-writing", "exploratory-data-analysis"
    ],

    "skill_catalog_last_updated": "2026-02-13T10:00:00Z"
  }
}
```

## Implementation Steps

### During Initialization Phase

```markdown
1. CHECK for Claude_Skills_中文指南.md
   - Location: {{PROJECT_DIR}}/Claude_Skills_中文指南.md
   - If exists: Read and parse
   - Store skill catalog in state.json

2. PARSE skill categories and capabilities
   - Extract skill names and descriptions
   - Build task-to-skill mapping

3. PLAN skill usage for each feature
   - For each feature in features.json:
     - Analyze feature description
     - Match against skill catalog
     - Add recommended_skills to feature
```

### During Implementation Phase

```markdown
1. BEFORE each implementation step:
   - Check step's invoke_skill field
   - Or analyze step description for skill match

2. INVOKE skill using Skill tool:
   - Skill tool with skill: {skill_name}
   - Execute with skill guidance

3. LOG skill invocation:
   - Update state.json skill_dispatch.skills_invoked
   - Record outcome and timestamp
```

## Common Skill Dispatch Patterns

### Pattern 1: Data Analysis Project

```yaml
Feature: Data Analysis Pipeline
Steps:
  1. Load data → invoke: exploratory-data-analysis
  2. Clean data → invoke: exploratory-data-analysis
  3. Analyze → invoke: statistical-analysis
  4. Visualize → invoke: data-artist
  5. Report → invoke: report-generator
```

### Pattern 2: ML Model Development

```yaml
Feature: ML Model Training
Steps:
  1. Feature engineering → invoke: engineering-features-for-machine-learning
  2. Model training → invoke: pytorch-lightning
  3. Evaluation → invoke: evaluating-machine-learning-models
  4. Interpretation → invoke: shap
  5. Documentation → invoke: docs-write
```

### Pattern 3: Code Quality Improvement

```yaml
Feature: Code Refactoring
Steps:
  1. Review code → invoke: code-reviewer
  2. Debug issues → invoke: debugging-strategies
  3. Optimize performance → invoke: performance-testing
  4. Update architecture → invoke: architecture-patterns
  5. Write tests → invoke: property-based-testing
```

## Error Handling

### Skill Not Available

```markdown
IF skill is recommended but not found:
  1. Log warning: "Skill {name} not available"
  2. Use built-in knowledge instead
  3. Continue with alternative approach
  4. Do NOT pause or ask user
```

### Skill Invocation Failure

```markdown
IF skill invocation fails:
  1. Log error to state.json
  2. Retry with alternative skill if available
  3. Fall back to built-in knowledge
  4. Continue execution
```

## Quick Reference

### How to Use in Autonomous Mode

1. **Place guide in workspace**: Copy `Claude_Skills_中文指南.md` to project root
2. **Run autonomous-builder**: It auto-detects and uses the guide
3. **Skills are auto-dispatched**: No manual intervention needed

### Manual Skill Dispatch

If specific skill is needed:

```
Using Skill tool: invoke skill_name
```

### Check Skill State

```
Read .builder/state.json → skill_dispatch section
```
