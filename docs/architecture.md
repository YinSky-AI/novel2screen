# Novel2Screen Architecture

## System Overview
Multi-Agent System for Novel-to-Screenplay Conversion

## Workflow
Upload -> Parser -> Segmenter -> ModeRouter -> Agents -> YAMLCompiler -> Critic -> Repair -> Export

## Agents
- NarrativeAgent: Extracts plot, subplots, turning points
- CharacterAgent: Extracts character profiles
- WorldAgent: Builds world rules (long mode)
- TimelineAgent: Chronological event ordering
- EpisodePlanner: Episode structure
- ScenePlanner: Scene layout
- DialogueAgent: Screenplay dialogue
- CriticAgent: Quality evaluation
- RepairAgent: Auto-fix issues
