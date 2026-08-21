from __future__ import annotations

import itertools
import re

from .model import Action, AuthorityScope, ResolutionStatus, SourceChannel, WorldState


class ActionCompiler:
    """Deterministic compiler with explicit principal/actor trust and R002 symbolic interaction verbs."""

    _counter = itertools.count(1)

    VERB_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("SPEAK", ("说", "告诉", "喊", "骂", "say", "tell", "shout", "insult")),
        ("OPEN", ("打开", "推开", "open")),
        ("CLOSE", ("关上", "关闭", "close")),
        ("HIT", ("打", "揍", "砸", "击", "punch", "hit", "strike")),
        ("DROP", ("放下", "丢下", "drop")),
        ("THROW", ("扔", "投掷", "throw")),
        ("PICK", ("捡", "拿起", "拾起", "pick", "grab")),
        ("WALK", ("走", "过去", "walk")),
        ("RUN", ("跑", "冲", "run")),
        ("LOOK", ("看", "观察", "look", "inspect")),
    )

    def compile(
        self,
        text: str,
        actor_id: str,
        world: WorldState,
        principal_id: str | None = None,
    ) -> Action:
        normalized = text.strip()
        verb = self._detect_verb(normalized)
        targets = self._detect_entities(normalized, world)
        source_channel = (
            SourceChannel.PLAYER_DIEGETIC_SPEECH
            if verb == "SPEAK"
            else SourceChannel.PLAYER_ACTION_DECLARATION
        )
        may_control_actor = world.can_principal_control(principal_id, actor_id)

        action = Action(
            action_id=f"A{next(self._counter):06d}",
            principal_id=principal_id,
            actor_id=actor_id,
            verb=verb,
            source_channel=source_channel,
            literal_user_input=normalized,
            target_ids=targets,
            declared_intent={"goal": normalized},
            preconditions=self._preconditions_for(verb, targets),
            authority_scope=AuthorityScope(may_control_actor=may_control_actor),
        )
        if verb == "UNKNOWN":
            action.resolution_status = ResolutionStatus.UNKNOWN_REQUIRES_DISAMBIGUATION
            action.failure_reason = "NO_SUPPORTED_ACTION_VERB"
        return action

    def _detect_verb(self, text: str) -> str:
        lowered = text.lower()
        for verb, patterns in self.VERB_PATTERNS:
            if any(pattern in lowered for pattern in patterns):
                return verb
        return "UNKNOWN"

    @staticmethod
    def _detect_entities(text: str, world: WorldState) -> list[str]:
        lowered = text.lower()
        matches: list[str] = []
        for actor_id, actor in world.actors.items():
            if actor_id.lower() in lowered or actor.name.lower() in lowered:
                matches.append(actor_id)
        for object_id, obj in world.objects.items():
            if object_id.lower() in lowered or obj.name.lower() in lowered:
                matches.append(object_id)
        for npc_id in world.npc_minds:
            if npc_id.lower() in lowered and npc_id not in matches:
                matches.append(npc_id)
        for zone_id in world.zone_scene_bindings:
            if zone_id.lower() in lowered and zone_id not in matches:
                matches.append(zone_id)
        return matches

    @staticmethod
    def _preconditions_for(verb: str, targets: list[str]) -> list[str]:
        conditions: list[str] = []
        if targets:
            conditions.append("TARGET_EXISTS")

        if verb == "HIT":
            conditions.extend(("TARGET_REACHABLE", "CAPABILITY_PRESENT"))
        elif verb == "SPEAK":
            conditions.append("CAPABILITY_PRESENT")
        elif verb == "PICK":
            conditions.extend(
                (
                    "TARGET_REACHABLE",
                    "CAPABILITY_PRESENT",
                    "AFFORDANCE_PRESENT",
                    "TARGET_GRASPABLE",
                    "FREE_HAND_AVAILABLE",
                    "TARGET_UNPOSSESSED",
                )
            )
        elif verb in {"DROP", "THROW"}:
            conditions.extend(
                (
                    "CAPABILITY_PRESENT",
                    "AFFORDANCE_PRESENT",
                    "POSSESSION_REQUIRED",
                )
            )
        elif verb in {"OPEN", "CLOSE"}:
            conditions.extend(
                (
                    "TARGET_REACHABLE",
                    "CAPABILITY_PRESENT",
                    "AFFORDANCE_PRESENT",
                )
            )
        elif verb == "WALK":
            conditions.extend(("CAPABILITY_PRESENT", "ADJACENT_ZONE"))
        return conditions


def declared_superhuman_effect(text: str) -> bool:
    """Conservative gate for explicit impossible normal-human declarations."""

    lowered = text.lower()
    chinese = re.search(r"一拳.*(?:五|5|六|6|七|7|八|8|九|9|十|10).*?(?:飞|倒)", lowered)
    english = re.search(
        r"one punch.*(?:five|5|six|6|seven|7|eight|8|nine|9|ten|10).*?(?:flying|meters)",
        lowered,
    )
    return bool(chinese or english)
