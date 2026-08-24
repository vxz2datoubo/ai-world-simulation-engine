# Interactive Cinema Game System Map

Status: `CANDIDATE_RESEARCH_MAPPING / NOT_RUNTIME_AUTHORIZATION`

This document makes the movie-game program navigable for a non-specialist without
turning any candidate into a production claim. The companion skill is
`skills/INTERACTIVE-CINEMA-GAME-SYSTEM-MAPPING-SKILL.yaml`.

## The product in one sentence

The player may attempt meaningful actions in a persistent world; the world resolves
what happened; a director turns only the permitted consequences into a cinematic
presentation; a renderer produces a fallible projection; and evaluation turns real
failures into tested learning.

## Four knowledge lenses

| Lens | Meaning | Example | Required handling |
| --- | --- | --- | --- |
| K0 | User explicitly said it | “Player choice must have real consequence.” | Retain source and do not dilute it. |
| K1 | Evidence-backed inference | Repeated user preference for delayed, restrained performances. | Keep evidence, confidence and override path. |
| K2 | Explainable professional knowledge | Storylet, dramatic agency, event sourcing, LOD. | Explain plainly and test locally. |
| K3 | Material unknown | Best renderer cost/latency or a final balance formula. | Register the unknown, owner and revalidation gate. |

K1 never silently becomes K0. K2 never becomes a project rule solely because a
paper, vendor or expert says it works. K3 is a first-class design object, not a
hole to cover with model prose.

## System relationship map

```text
Player intent (untrusted)
        |
        v
Action DSL -> authority / affordance / physics / capability gates
        |                                      |
        | reject, ask, partial, or resolve     | no narrative override
        v                                      v
Canonical event history ----> replayable world state
        |
        +--> recipient-specific knowledge / memory
        |
        +--> legal narrative opportunity and PX ranking candidates
                         |
                         v
              AWRSE DIRECTOR-BEAT-PACKET
                         |
                         v
      AI Film shot / sound / edit / staging compiler
                         |
                         v
           Renderer candidate media (non-authoritative)
                         |
                         v
     observations + user verdict + A/B evidence + regressions
                         |
                         v
       candidate learning -> governed promotion, if justified
```

The arrows point in one direction for authority. A renderer cannot send pixels
back to mutate the world. A director cannot repair a failed action by staging a
success. A narrative system can rank only legal opportunities.

## What already runs, what is only designed

| Layer | Current evidence | Meaning for the project |
| --- | --- | --- |
| World truth and action resolution | Accepted R001/R002 reference runtime | Core free-text action, authority/affordance checks, events and replay are present. |
| Solo persistence and replay inspection | Accepted R003-I1A/I1B reference runtime | A single-player reference state can rebuild from canonical evidence. |
| Capability/injury | AF-C interface; PR #29 still requires changes | Do not implement combat/balance/progression until the machine contract separates architecture from deferred tuning. |
| Memory, story, opportunity, PX | AF-E/F/G interfaces | Useful designs exist but are not a license to ship an LLM-driven narrative layer. |
| Director handoff | AF-H interface plus AI Film system | The transfer shape is defined; a runtime packet assembler is not yet released. |
| Renderer | Provisional strategy | H3/Matrix-style routing is an experiment, not a product capability claim. |

## External evidence and how it changes the design

1. [Unreal Mass Entity](https://dev.epicgames.com/documentation/unreal-engine/overview-of-mass-entity-in-unreal-engine?lang=en-US), [Mass Gameplay](https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-mass-gameplay-in-unreal-engine) and [Smart Objects](https://dev.epicgames.com/documentation/unreal-engine/smart-objects-in-unreal-engine---overview?lang=en-US) provide useful adapter ideas: data-only fragments, processors, representation LOD and reserved interaction slots. They support a scale path, but they do not replace AWRSE's event authority or make an Unreal integration approved.

2. [Ink](https://github.com/inkle/ink) demonstrates authorable branching and
recombination for interactive scripts. Its key lesson for AWRSE is that authored
flow should be an input to opportunity selection, not a second database of what
really happened. The [80 Days postmortem](https://gdcvault.com/play/1021717/80-DAYS-Post-mortem-Letting)
is a product-scale reminder to compose narrative from circumstance rather than
enumerating every possible player branch.

3. AAAI/AIIDE research on [personalized drama management](https://ojs.aaai.org/index.php/AIIDE/article/view/12665)
and [authorial leverage](https://ojs.aaai.org/index.php/AIIDE/article/view/12377)
frames the central tradeoff: authorial guidance must be measured against player
agency. In AWRSE this becomes a hard architecture rule: PX can rank candidates,
but cannot create facts, reveal unavailable knowledge or secretly change a hard
capability result.

4. Recent research, such as [Orchestrated Reality](https://arxiv.org/abs/2606.16014),
[RPGBench](https://arxiv.org/abs/2502.00595) and
[NCP-Bench](https://arxiv.org/abs/2608.08160), reinforces a risk already addressed
by the project: fluent LLM output is not evidence of persistent coherence. These
are research leads and benchmark candidates, not evidence that any model or
architecture is production-ready.

5. The AI Film repository supplies the existing director-side complement:
director routing, shot-local visible/audible constraints, director pulls and
mechanism-level learning. Its internal rule that observation, interpretation,
prompt hypothesis and unknown must remain separate matches this map's K0–K3
discipline.

6. Google DeepMind's [SIMA](https://deepmind.google/blog/sima-generalist-ai-agent-for-3d-virtual-environments/)
and [Genie 3](https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/),
and NVIDIA's [Cosmos](https://research.nvidia.com/labs/dir/cosmos1/), are useful
signals of rapidly improving interactive and world-model capability. They do not
alter the authority diagram: any such model belongs behind a versioned adapter and
must be assessed against AWRSE packets, replay consistency, latency and cost. Its
output cannot become a canonical world event merely because it looks plausible.

7. [OWASP prompt-injection guidance](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
and its [AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
add a mandatory hostile-input frame. Player text, retrieved knowledge, media
metadata, tickets and external API responses are data, never authority or
instructions. A future agent or renderer integration needs typed-output checks,
least-privilege tool boundaries, memory isolation and prompt-injection regression
cases before it can act on any project-controlled resource.

## The next honest release sequence

1. **Repair PR #29.** Make AF-C lifecycle and `ActorBaseProfile` provenance
   machine-readable. It is an architecture/governance repair, not runtime work;
   it does not itself release I2.
2. **Resolve the lower-layer decision gate, or grant a bounded exemption.** The
   current CAP-EVAL evidence explicitly remains `KEEP_ATTR_OPEN` and
   `KEEP_MATH_OPEN`. I2 therefore needs either accepted current decisions for the
   exact semantics it consumes, or a separate, independently reviewed exemption
   that names the permitted non-controversial semantics, excludes formula/balance
   tuning, fails closed outside that envelope and carries a Control Tower runtime
   release. A historical lifecycle label is not an exemption.
3. **Release I2 as a tiny capability feasibility reference.** One obstacle, two
   versioned character profiles, a hard feasibility gate, a separate hazard axis,
   event receipt and exact replay. No combat system, balance claim or progression.
4. **Release a Director Packet reference loop.** One already-resolved canonical
   event must yield a packet containing confirmed facts, visibility limits and
   presentation requirements. Perform an AI Film dry-run only; do not call a
   provider or alter the world from media.
5. **Add a controlled renderer experiment.** Evaluate the same packet across
   selected backends for action fidelity, identity/scene continuity, latency,
   cost and unauthorized-hallucination rate. Revalidate provider documentation at
   the exact version before any routing decision.
6. **Only then evaluate broader systems.** NPC memory, storylets, World Echo,
   party/public topology and experience ranking must each receive a bounded
   contract, adversarial tests, independent review and a separate release.

## Concrete acceptance questions

For each vertical slice, a reviewer should be able to answer yes to all of these:

- What is the one canonical fact source?
- Which inputs are untrusted, and where do they stop?
- What can the director, renderer and public audience read, and what can none of
  them mutate?
- Which claims are observed, inferred, candidate knowledge and unknown?
- Can a replay reproduce the same authoritative state?
- Does an invalid external response fail closed rather than fabricate a result?
- Which test would falsify the slice's claimed value?

If any answer is absent, the slice is a design candidate, not a completed
movie-game capability.
