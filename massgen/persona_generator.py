# -*- coding: utf-8 -*-
"""Automatic persona generation for MassGen agents.

This module provides functionality to automatically generate diverse system
messages (personas) for MassGen agents using an LLM, increasing response
diversity without requiring users to manually craft different system messages.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class GeneratedPersona:
    """A persona generated for an agent.

    Attributes:
        agent_id: The ID of the agent this persona is for
        persona_text: The full persona instruction text
        attributes: Additional attributes describing the persona style
    """

    agent_id: str
    persona_text: str
    attributes: Dict[str, str]


@dataclass
class PersonaGeneratorConfig:
    """Configuration for automatic persona generation.

    Attributes:
        enabled: Whether persona generation is enabled
        backend: Backend configuration for the LLM to use for generation
        strategy: Generation strategy (complementary, diverse, specialized, adversarial)
        persona_guidelines: Optional custom guidelines for persona generation
    """

    enabled: bool = False
    backend: Dict[str, Any] = None
    strategy: str = "complementary"
    persona_guidelines: Optional[str] = None

    def __post_init__(self):
        if self.backend is None:
            self.backend = {"type": "openai", "model": "gpt-4o-mini"}


class PersonaGenerator:
    """Generates diverse personas for MassGen agents using an LLM.

    The generator creates complementary personas that encourage diverse
    perspectives when multiple agents tackle the same problem.

    Example:
        >>> from massgen.persona_generator import PersonaGenerator, PersonaGeneratorConfig
        >>> from massgen.cli import create_backend
        >>>
        >>> config = PersonaGeneratorConfig(
        ...     enabled=True,
        ...     backend={"type": "openai", "model": "gpt-4o-mini"},
        ...     strategy="complementary"
        ... )
        >>> backend = create_backend(**config.backend)
        >>> generator = PersonaGenerator(
        ...     backend=backend,
        ...     strategy=config.strategy,
        ...     guidelines=config.persona_guidelines
        ... )
        >>> personas = await generator.generate_personas(
        ...     agent_ids=["agent_a", "agent_b", "agent_c"],
        ...     task="Analyze this code for bugs",
        ...     existing_system_messages={}
        ... )
    """

    def __init__(
        self,
        backend: Any,
        strategy: str = "complementary",
        guidelines: Optional[str] = None,
    ):
        """Initialize the persona generator.

        Args:
            backend: LLM backend to use for generation
            strategy: Generation strategy (complementary, diverse, specialized, adversarial)
            guidelines: Optional custom guidelines for persona generation
        """
        self.backend = backend
        self.strategy = strategy
        self.guidelines = guidelines

    async def generate_personas(
        self,
        agent_ids: List[str],
        task: str,
        existing_system_messages: Dict[str, Optional[str]],
    ) -> Dict[str, GeneratedPersona]:
        """Generate diverse personas for all agents.

        Args:
            agent_ids: List of agent IDs to generate personas for
            task: The task/query agents will work on
            existing_system_messages: Existing system messages (to enhance, not replace)

        Returns:
            Dictionary mapping agent_id to GeneratedPersona
        """
        if not agent_ids:
            logger.warning("No agent IDs provided for persona generation")
            return {}

        prompt = self._build_generation_prompt(agent_ids, task, existing_system_messages)

        logger.info(f"Generating personas for {len(agent_ids)} agents using strategy: {self.strategy}")

        try:
            # Use stream_with_tools with empty tools to generate text
            response_content = await self._generate_response(prompt)
            personas = self._parse_response(response_content, agent_ids)

            # Log summary
            for agent_id, persona in personas.items():
                style = persona.attributes.get("thinking_style", "unknown")
                logger.debug(f"Generated persona for {agent_id}: {style}")

            return personas

        except Exception as e:
            logger.error(f"Failed to generate personas: {e}")
            logger.info("Using fallback personas")
            return self._generate_fallback_personas(agent_ids)

    async def _generate_response(self, prompt: str) -> str:
        """Generate a response from the LLM backend.

        Args:
            prompt: The prompt to send to the LLM

        Returns:
            The generated response text
        """
        messages = [{"role": "user", "content": prompt}]

        # Collect streaming response
        response_parts = []

        # Get model from backend config, with fallback
        model = self.backend.config.get("model", "gpt-4o-mini")

        async for chunk in self.backend.stream_with_tools(messages=messages, tools=[], model=model):
            if chunk.content:
                response_parts.append(chunk.content)

        return "".join(response_parts)

    def _build_generation_prompt(
        self,
        agent_ids: List[str],
        task: str,
        existing_system_messages: Dict[str, Optional[str]],
    ) -> str:
        """Build the prompt for persona generation.

        Args:
            agent_ids: List of agent IDs
            task: The task description
            existing_system_messages: Existing system messages per agent

        Returns:
            The formatted prompt string
        """
        strategy_instructions = self._get_strategy_instructions()

        # Build agent context
        agents_context = []
        for agent_id in agent_ids:
            existing = existing_system_messages.get(agent_id)
            if existing:
                agents_context.append(f"- {agent_id}: Has existing instruction:\n{existing}")
            else:
                agents_context.append(f"- {agent_id}: No existing instruction")

        agents_list = "\n".join(agents_context)
        agent_ids_json = json.dumps(agent_ids)

        prompt = f"""Generate diverse personas for {len(agent_ids)} AI agents working collaboratively on a task.

## Task
{task}

## Agents
{agents_list}

## Strategy: {self.strategy}
{strategy_instructions}

## Guidelines
{self.guidelines or "Generate personas that encourage diverse, high-quality responses."}

## Requirements
1. Each persona should be detailed, as it will be used for a system prompt for an agent.
2. Personas should be complementary - cover different aspects/approaches
3. Include specific thinking styles, focuses, and communication patterns
4. If an agent has an existing instruction, enhance it rather than replace it
5. Make personas specific enough to influence behavior but general enough to apply to any subtask
6. **CRITICAL**: All agents must solve the ENTIRE task completely. Do NOT create
   specialized roles or divide the task into subtasks. Each agent should produce a
   complete solution to the task with their unique perspective/approach. Personas add
   diversity in HOW to solve the task, NOT which part to solve.

## Output Format
Return a JSON object with this structure:
{{
    "personas": {{
        "<agent_id>": {{
            "persona_text": "The full persona instruction text...",
            "attributes": {{
                "thinking_style": "analytical|creative|systematic|intuitive",
                "focus_area": "details|big-picture|risks|opportunities",
                "communication": "concise|thorough|example-driven|principle-based"
            }}
        }}
    }}
}}

Important: The agent_ids you must generate personas for are: {agent_ids_json}

Generate personas now:"""

        return prompt

    def _get_strategy_instructions(self) -> str:
        """Get instructions based on generation strategy.

        Returns:
            Strategy-specific instructions string
        """
        strategies = {
            "complementary": """Create personas that complement each other:
- Cover different aspects of the problem
- Use different analytical approaches
- Balance risk-awareness with innovation
- Ensure all major perspectives are represented""",
            "diverse": """Maximize diversity across personas:
- Each should have a distinctly different viewpoint
- Vary thinking styles significantly
- Include contrarian perspectives
- Embrace unconventional approaches""",
            "specialized": """Create specialized expert personas:
- Each should have deep expertise in a specific area
- Focus on different technical/domain aspects
- Provide domain-specific insights
- Reference relevant best practices and patterns""",
            "adversarial": """Create constructively adversarial personas:
- Include devil's advocate perspectives
- Challenge assumptions and proposals
- Probe for weaknesses and edge cases
- Balance criticism with constructive alternatives""",
        }
        return strategies.get(self.strategy, strategies["complementary"])

    def _parse_response(self, response: str, agent_ids: List[str]) -> Dict[str, GeneratedPersona]:
        """Parse LLM response into GeneratedPersona objects.

        Args:
            response: The raw LLM response
            agent_ids: Expected agent IDs

        Returns:
            Dictionary mapping agent_id to GeneratedPersona
        """
        try:
            # Try to extract JSON from the response
            # The response might contain markdown code blocks
            json_str = response

            # Remove markdown code block if present
            if "```json" in json_str:
                start = json_str.find("```json") + 7
                end = json_str.find("```", start)
                json_str = json_str[start:end].strip()
            elif "```" in json_str:
                start = json_str.find("```") + 3
                end = json_str.find("```", start)
                json_str = json_str[start:end].strip()

            data = json.loads(json_str)
            personas = {}

            for agent_id in agent_ids:
                if agent_id in data.get("personas", {}):
                    persona_data = data["personas"][agent_id]
                    personas[agent_id] = GeneratedPersona(
                        agent_id=agent_id,
                        persona_text=persona_data.get("persona_text", "Approach this task thoughtfully."),
                        attributes=persona_data.get("attributes", {}),
                    )
                else:
                    # Fallback if agent not in response
                    logger.warning(f"No persona generated for agent {agent_id}, using default")
                    personas[agent_id] = GeneratedPersona(
                        agent_id=agent_id,
                        persona_text="Approach this task thoughtfully and thoroughly.",
                        attributes={},
                    )

            return personas

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse persona response: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            return self._generate_fallback_personas(agent_ids)

    def _generate_fallback_personas(self, agent_ids: List[str]) -> Dict[str, GeneratedPersona]:
        """Generate simple fallback personas if LLM generation fails.

        Args:
            agent_ids: List of agent IDs

        Returns:
            Dictionary mapping agent_id to GeneratedPersona with default personas
        """
        fallback_templates = [
            (
                "analytical",
                "You approach problems analytically, breaking them down into components and examining each carefully. Focus on logical reasoning and evidence-based conclusions.",
            ),
            (
                "creative",
                "You think creatively, looking for innovative solutions and unconventional approaches. Don't be afraid to suggest novel ideas that others might overlook.",
            ),
            (
                "systematic",
                "You work systematically, ensuring thorough coverage and consistent methodology. Pay attention to process and make sure no important details are missed.",
            ),
            (
                "critical",
                "You take a critical perspective, questioning assumptions and identifying potential issues. Your role is to probe for weaknesses and ensure robustness.",
            ),
            (
                "practical",
                "You focus on practical implementation, considering real-world constraints and feasibility. Prioritize actionable solutions over theoretical ideals.",
            ),
        ]

        personas = {}
        for i, agent_id in enumerate(agent_ids):
            style, text = fallback_templates[i % len(fallback_templates)]
            personas[agent_id] = GeneratedPersona(
                agent_id=agent_id,
                persona_text=text,
                attributes={
                    "thinking_style": style,
                    "focus_area": "general",
                    "communication": "balanced",
                },
            )
            logger.debug(f"Using fallback persona for {agent_id}: {style}")

        return personas
