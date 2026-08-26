import copy
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PARENT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
EVAL_PATH = ROOT / "evals" / "AF001-ASSET-SPATIAL-CONFORMANCE.json"

CARDINALS = {"N", "S", "E", "W"}
REQUIRED_PARENT_TYPES = {
    "WorldFrame", "Scene", "Zone", "Portal", "CameraAnchor", "View",
    "MediaAsset", "MediaVersion", "Locator",
}
DYNAMIC_ASSET_FIELDS = {
    "actor_state_ref", "object_state_ref", "presentation_state_ref", "outfit_state_ref",
    "dressing_state_ref", "injury_state_ref", "scene_dynamic_state_ref",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _by_id(items, key):
    result = {}
    for item in items:
        value = item[key]
        if value in result:
            raise AssertionError(f"DUPLICATE_ID:{key}:{value}")
        result[value] = item
    return result


def _validate_fixture(doc):
    fixture = doc["synthetic_fixture"]
    objects = fixture["canonical_objects"]
    projections = fixture["eval_only_projections"]

    world_frames = _by_id(objects["WorldFrame"], "world_frame_id")
    scenes = _by_id(objects["Scene"], "scene_id")
    zones = _by_id(objects["Zone"], "zone_id") if objects["Zone"] else {}
    portals = _by_id(objects["Portal"], "portal_id")
    anchors = _by_id(objects["CameraAnchor"], "camera_anchor_id")
    views = _by_id(objects["View"], "view_id")
    assets = _by_id(objects["MediaAsset"], "media_asset_id")
    versions = _by_id(objects["MediaVersion"], "media_version_id")
    locators = _by_id(objects["Locator"], "locator_id")

    if len(world_frames) != 1:
        return "WORLD_FRAME_CARDINAL_AUTHORITY_INVALID"
    world_frame = next(iter(world_frames.values()))
    canonical_north = world_frame["canonical_north"]
    if canonical_north not in CARDINALS:
        return "WORLD_FRAME_CARDINAL_AUTHORITY_INVALID"

    graph = projections["spatial_graph"]
    text_map = projections["text_map_projection"]
    image_map = projections["image_map_projection"]
    graph_tuple = (graph["graph_id"], graph["graph_version"])
    if (text_map["graph_id"], text_map["graph_version"]) != graph_tuple:
        return "MAP_PROJECTION_GRAPH_BINDING_MISMATCH"
    if (image_map["graph_id"], image_map["graph_version"]) != graph_tuple:
        return "MAP_PROJECTION_GRAPH_BINDING_MISMATCH"
    if text_map["north_arrow"] != canonical_north or image_map["screen_top_cardinal"] != canonical_north:
        return "MAP_PROJECTION_ORIENTATION_MISMATCH"

    graph_edge_refs = [edge["portal_id"] for edge in graph["edges"]]
    if sorted(text_map["edge_refs"]) != sorted(graph_edge_refs):
        return "MAP_PROJECTION_TOPOLOGY_MISMATCH"
    if sorted(image_map["edge_refs"]) != sorted(graph_edge_refs):
        return "MAP_PROJECTION_TOPOLOGY_MISMATCH"

    known_spatial_ids = set(scenes) | set(zones)
    for portal in portals.values():
        if portal["from_scene_or_zone_id"] not in known_spatial_ids:
            return "PORTAL_ENDPOINT_UNKNOWN"
        if portal["to_scene_or_zone_id"] not in known_spatial_ids:
            return "PORTAL_ENDPOINT_UNKNOWN"

    for edge in graph["edges"]:
        if edge["semantic_class"] == "VERTICAL" and edge.get("cardinal") is not None:
            return "VERTICAL_TOPOLOGY_FALSE_CARDINAL"

    for anchor in anchors.values():
        if anchor["scene_id"] not in scenes:
            return "CAMERA_ANCHOR_SCENE_UNKNOWN"
        if anchor["position_semantics"] in CARDINALS:
            return "CAMERA_POSITION_FACING_CONFLATION"

    for view in views.values():
        if any(key in view for key in ("location", "locator_id", "media_version_id", "file_id", "filename")):
            return "VIEW_MUST_NOT_CONTAIN_MEDIA_LOCATOR"
        if view["scene_id"] not in scenes or view["camera_anchor_id"] not in anchors:
            return "VIEW_SPATIAL_BINDING_UNKNOWN"
        if anchors[view["camera_anchor_id"]]["scene_id"] != view["scene_id"]:
            return "VIEW_SPATIAL_BINDING_UNKNOWN"
        facing = view["facing_cardinal_optional"]
        screen_top = view["screen_top_cardinal_optional"]
        if facing is not None and facing not in CARDINALS:
            return "VIEW_CARDINAL_INVALID"
        if screen_top is not None and screen_top not in CARDINALS:
            return "VIEW_CARDINAL_INVALID"

    west_view = views["VIEW-WEST"]
    if anchors[west_view["camera_anchor_id"]]["position_semantics"] != "EAST_SIDE":
        return "EAST_SIDE_WEST_FACING_PROBE_FAILED"
    if west_view["facing_cardinal_optional"] != "W":
        return "EAST_SIDE_WEST_FACING_PROBE_FAILED"

    for relation in projections["relations"]:
        if relation["relation_type"] == "EDITORIAL_SHOT_REVERSE_SHOT" and not relation["explicit_binding"]:
            return "VIEW_RELATION_REQUIRES_EXPLICIT_BINDING"
        if any(view_id not in views for view_id in relation["member_view_ids"]):
            return "VIEW_RELATION_MEMBER_UNKNOWN"

    seen_default_keys = set()
    for entry in projections["asset_selection"]:
        if entry["asset_id"] not in assets:
            return "ASSET_SELECTION_UNKNOWN_ASSET"
        if entry["is_default"]:
            key = tuple(entry["context_key"])
            if key in seen_default_keys:
                return "DUPLICATE_DEFAULT_ASSET_CONTEXT"
            seen_default_keys.add(key)

    for asset in assets.values():
        if DYNAMIC_ASSET_FIELDS.intersection(asset):
            return "DYNAMIC_STATE_CONTAMINATES_ASSET_IDENTITY"
        view_ref = asset["view_ref_optional"]
        if view_ref is not None and view_ref not in views:
            return "MEDIA_ASSET_VIEW_UNKNOWN"

    for version in versions.values():
        if version["media_asset_id"] not in assets:
            return "MEDIA_VERSION_ASSET_UNKNOWN"

    version_selection = projections["version_selection"]["by_asset"]
    for asset_id, selection in version_selection.items():
        if asset_id not in assets:
            return "VERSION_SELECTION_UNKNOWN_ASSET"
        lifecycle = selection["lifecycle"]
        current_ids = [version_id for version_id, state in lifecycle.items() if state == "CURRENT"]
        if len(current_ids) > 1:
            return "MULTIPLE_CURRENT_MEDIA_VERSIONS"
        if len(current_ids) != 1:
            return "CURRENT_MEDIA_VERSION_UNRESOLVED"
        current_id = selection["current_version_id"]
        if current_id != current_ids[0] or current_id not in versions:
            return "CURRENT_MEDIA_VERSION_UNRESOLVED"
        if versions[current_id]["media_asset_id"] != asset_id:
            return "CURRENT_MEDIA_VERSION_ASSET_MISMATCH"
        if versions[current_id]["verification_state"] != "VERIFIED":
            return "CURRENT_MEDIA_VERSION_NOT_VERIFIED"

    for locator in locators.values():
        if locator["media_version_id"] not in versions:
            return "LOCATOR_MEDIA_VERSION_UNKNOWN"

    migration = projections["locator_migration_probe"]
    if migration["before"]["asset_id"] != migration["after"]["asset_id"]:
        return "LOCATOR_MIGRATION_CHANGED_ASSET_OR_VERSION_IDENTITY"
    if migration["before"]["version_id"] != migration["after"]["version_id"]:
        return "LOCATOR_MIGRATION_CHANGED_ASSET_OR_VERSION_IDENTITY"

    probes = projections["revision_classification_probes"]
    same_pixels = probes["same_pixels_new_locator"]
    if same_pixels["old_hash"] == same_pixels["new_hash"] and same_pixels["old_version_id"] != same_pixels["proposed_version_id"]:
        return "SAME_PIXELS_MUST_REUSE_MEDIA_VERSION"

    changed = probes["changed_pixels_same_role"]
    if changed["old_hash"] != changed["new_hash"] and changed["old_version_id"] == changed["proposed_version_id"]:
        return "CHANGED_PIXELS_REQUIRE_NEW_MEDIA_VERSION"

    variant = probes["variant_change"]
    if variant["changed_dimensions"] and variant["old_asset_id"] == variant["proposed_asset_id"]:
        return "VARIANT_DIMENSION_CHANGE_REQUIRES_SEPARATE_ASSET"

    canonical_edges = {(edge["from"], edge["to"]) for edge in graph["edges"]}
    for edge in projections["renderer_probe"]["requested_edges"]:
        if tuple(edge) not in canonical_edges:
            return "RENDERER_TOPOLOGY_INVENTION"

    revisit = projections["revisit_probe"]
    if revisit["resolved_asset_id"] != revisit["initial_asset_id"] and revisit["identity_change_event_ref"] is None:
        return "REVISIT_CHANGED_STABLE_ASSET_IDENTITY_WITHOUT_EVENT"

    for pack in projections["story_asset_packs"]:
        if "embedded_assets" in pack:
            return "STORY_ASSET_PACK_MUST_REFERENCE_SHARED_IDENTITY"
        if any(asset_id not in assets for asset_id in pack["asset_refs"]):
            return "STORY_ASSET_PACK_UNKNOWN_ASSET"

    resolver = projections["resolver_probe"]
    if resolver["semantic_substitution_used"]:
        return "SEMANTIC_ASSET_SUBSTITUTION_FORBIDDEN"
    target_asset = resolver["target_asset_id"]
    current_id = version_selection[target_asset]["current_version_id"]
    usable = [locator for locator in locators.values() if locator["media_version_id"] == current_id and locator["status"] == "VERIFIED"]
    if not usable:
        if resolver["resolved_asset_id"] not in (None, target_asset):
            return "SEMANTIC_ASSET_SUBSTITUTION_FORBIDDEN"
        if resolver["state"] != "ASSET_UNAVAILABLE":
            return "ASSET_UNAVAILABLE_NOT_EXPLICIT"
    elif resolver["resolved_asset_id"] != target_asset:
        return "SEMANTIC_ASSET_SUBSTITUTION_FORBIDDEN"

    direction_probe = projections["direction_inference_probe"]
    if direction_probe["source"] in {"FILENAME", "OPAQUE_ID", "LEGACY_NAME_TOKEN"}:
        return "DIRECTION_INFERENCE_FROM_FILENAME_OR_OPAQUE_ID_FORBIDDEN"

    if projections["generation_probe"]["canonical_mutation_requested"]:
        return "GENERATED_MEDIA_CANNOT_MUTATE_CANONICAL_STATE"

    return None


def _mutate(doc, mutation):
    if mutation == "NONE":
        return
    p = doc["synthetic_fixture"]["eval_only_projections"]
    o = doc["synthetic_fixture"]["canonical_objects"]

    if mutation == "MAP_GRAPH_ID_DRIFT":
        p["image_map_projection"]["graph_id"] = "SG-OTHER"
    elif mutation == "MAP_NORTH_DRIFT":
        p["image_map_projection"]["screen_top_cardinal"] = "S"
    elif mutation == "CAMERA_POSITION_FACING_CONFLATION":
        o["CameraAnchor"][0]["position_semantics"] = "W"
    elif mutation == "INFERRED_SHOT_REVERSE":
        p["relations"].append({"construct":"ExplicitViewRelationFixture","authority":"NONCANONICAL_EVAL_ONLY","relation_id":"REL-BAD-INFERRED","relation_type":"EDITORIAL_SHOT_REVERSE_SHOT","member_view_ids":["VIEW-WEST","VIEW-EAST"],"explicit_binding":False})
    elif mutation == "DUPLICATE_DEFAULT_ASSET":
        duplicate = copy.deepcopy(p["asset_selection"][0]); duplicate["asset_id"] = "AST-NIGHT-WEST"; p["asset_selection"].append(duplicate)
    elif mutation == "TWO_CURRENT_VERSIONS":
        p["version_selection"]["by_asset"]["AST-DAY-WEST"]["lifecycle"]["VER-DAY-WEST-OLD"] = "CURRENT"
    elif mutation == "LOCATOR_MIGRATION_MINTS_IDENTITY":
        p["locator_migration_probe"]["after"]["version_id"] = "VER-DAY-WEST-OLD"
    elif mutation == "SAME_PIXELS_MINTS_VERSION":
        p["revision_classification_probes"]["same_pixels_new_locator"]["proposed_version_id"] = "VER-SAME-2"
    elif mutation == "CHANGED_PIXELS_REUSE_VERSION":
        p["revision_classification_probes"]["changed_pixels_same_role"]["proposed_version_id"] = "VER-REV-1"
    elif mutation == "VARIANT_AS_REVISION":
        p["revision_classification_probes"]["variant_change"]["proposed_asset_id"] = "AST-DAY-WEST"
    elif mutation == "MAP_EDGE_DISAGREEMENT":
        p["image_map_projection"]["edge_refs"] = ["PORTAL-EAST"]
    elif mutation == "UNKNOWN_PORTAL_ENDPOINT":
        o["Portal"][0]["to_scene_or_zone_id"] = "SCN-UNKNOWN"
    elif mutation == "VERTICAL_FLATTENED_CARDINAL":
        p["spatial_graph"]["edges"][1]["cardinal"] = "N"; o["Portal"][1]["relation_type"] = "CARDINAL_NORTH"
    elif mutation == "RENDERER_INVENTS_TOPOLOGY":
        p["renderer_probe"]["requested_edges"].append(["SCN-PLAZA", "SCN-TOWER"])
    elif mutation == "DYNAMIC_STATE_IN_ASSET":
        o["MediaAsset"][0]["actor_state_ref"] = "ACTOR-DYNAMIC-STATE"
    elif mutation == "REVISIT_MINTS_NEW_ASSET":
        p["revisit_probe"]["resolved_asset_id"] = "AST-DAY-EAST"
    elif mutation == "UNVERIFIED_CURRENT":
        next(v for v in o["MediaVersion"] if v["media_version_id"] == "VER-DAY-WEST-1")["verification_state"] = "PENDING"
    elif mutation == "PACK_EMBEDS_ASSET":
        p["story_asset_packs"][0]["embedded_assets"] = [copy.deepcopy(o["MediaAsset"][0])]
    elif mutation == "STALE_LOCATOR_SEMANTIC_SUBSTITUTE":
        for locator in o["Locator"]:
            if locator["media_version_id"] == "VER-DAY-WEST-1": locator["status"] = "STALE"
        p["resolver_probe"].update({"resolved_asset_id":"AST-DAY-EAST","state":"RESOLVED","semantic_substitution_used":True})
    elif mutation == "DIRECTION_FROM_FILENAME":
        p["direction_inference_probe"] = {"source":"FILENAME","inferred_cardinal":"N"}
    elif mutation == "VIEW_AS_FILE":
        o["View"][0]["location"] = "memory://not-a-view"
    elif mutation == "GENERATED_PIXELS_MUTATE_TOPOLOGY":
        p["generation_probe"]["canonical_mutation_requested"] = True
    else:
        raise AssertionError(f"UNKNOWN_MUTATION:{mutation}")


def test_eval_binds_exact_canonical_parent_and_existing_type_authorities():
    parent = load_json(PARENT_PATH); doc = load_json(EVAL_PATH)
    assert doc["canonical_parent"] == {"contract_id":parent["contract_id"],"contract_version":parent["contract_version"],"authority_graph_version":parent["authority_graph_version"]}
    assert set(doc["required_parent_type_bindings"]) == REQUIRED_PARENT_TYPES
    for name, expected in doc["required_parent_type_bindings"].items():
        actual = parent["type_registry"][name]
        assert actual["type_id"] == expected["type_id"]
        assert actual["version"] == expected["version"]
        assert actual["authority_profile_ref"] == expected["authority_profile_ref"]
    invariants = parent["freeze_domains"]["AF-D"]["invariants"]
    for expected in ("CAMERA_POSITION_NE_CAMERA_FACING","MEDIA_ASSET_IDENTITY_NE_MEDIA_VERSION_NE_LOCATOR","LOCATOR_MIGRATION_NE_ASSET_OR_VERSION_IDENTITY_CHANGE","GENERATED_PIXELS_CANNOT_CREATE_CANONICAL_STATE"):
        assert expected in invariants


def test_fixture_canonical_objects_do_not_invent_parent_fields():
    parent = load_json(PARENT_PATH); doc = load_json(EVAL_PATH)
    for type_name, items in doc["synthetic_fixture"]["canonical_objects"].items():
        allowed = set(parent["type_registry"][type_name]["fields"])
        for item in items: assert set(item) <= allowed, (type_name, set(item) - allowed)


def test_fixture_only_constructs_are_explicitly_noncanonical_and_do_not_mint_types():
    parent = load_json(PARENT_PATH); doc = load_json(EVAL_PATH); boundary = doc["authority_boundary"]
    assert boundary["does_not_register_new_canonical_types"] is True
    assert boundary["does_not_modify_parent_contract"] is True
    assert boundary["external_pattern_evidence_authority"] == "INSPIRATION_ONLY_NOT_AWRSE_AUTHORITY"
    assert boundary["fixture_only_semantics"].startswith("NONCANONICAL_EVAL_ONLY")
    future_type_gaps = {gap["name"] for gap in doc["future_parent_binding_gaps"] if gap["name"] != "MediaAssetCurrentVersionPointer"}
    assert future_type_gaps.isdisjoint(parent["type_registry"])
    def walk(value):
        if isinstance(value, dict):
            if "construct" in value: assert value.get("authority") == "NONCANONICAL_EVAL_ONLY"
            for child in value.values(): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(doc["synthetic_fixture"]["eval_only_projections"])


def test_base_synthetic_story_asset_graph_conforms():
    assert _validate_fixture(load_json(EVAL_PATH)) is None


def test_east_side_camera_can_face_west_without_identity_conflation():
    doc = load_json(EVAL_PATH); anchors = _by_id(doc["synthetic_fixture"]["canonical_objects"]["CameraAnchor"], "camera_anchor_id"); views = _by_id(doc["synthetic_fixture"]["canonical_objects"]["View"], "view_id")
    assert anchors["CAM-EAST"]["position_semantics"] == "EAST_SIDE"
    assert views["VIEW-WEST"]["camera_anchor_id"] == "CAM-EAST"
    assert views["VIEW-WEST"]["facing_cardinal_optional"] == "W"
    assert _validate_fixture(doc) is None


def test_opposite_cardinals_do_not_create_editorial_shot_reverse_shot():
    doc = load_json(EVAL_PATH); relations = doc["synthetic_fixture"]["eval_only_projections"]["relations"]
    assert all(relation["relation_type"] != "EDITORIAL_SHOT_REVERSE_SHOT" for relation in relations)
    assert _validate_fixture(doc) is None


def test_shared_asset_pack_reuse_preserves_one_logical_identity_by_reference():
    packs = load_json(EVAL_PATH)["synthetic_fixture"]["eval_only_projections"]["story_asset_packs"]
    assert "AST-DAY-WEST" in packs[0]["asset_refs"] and "AST-DAY-WEST" in packs[1]["asset_refs"]
    assert all("embedded_assets" not in pack for pack in packs)


@pytest.mark.parametrize("case", load_json(EVAL_PATH)["adversarial_cases"], ids=lambda case: case["case_id"])
def test_adversarial_asset_spatial_cases(case):
    doc = load_json(EVAL_PATH); _mutate(doc, case["mutation"])
    assert _validate_fixture(doc) == case["expected_error"]


def test_required_case_family_is_complete_and_unique():
    cases = load_json(EVAL_PATH)["adversarial_cases"]; ids = [case["case_id"] for case in cases]
    assert len(ids) == len(set(ids)) and len(ids) >= 20
    required = {"MAP_GRAPH_ID_DRIFT","MAP_NORTH_DRIFT","CAMERA_POSITION_FACING_CONFLATION","INFERRED_SHOT_REVERSE","DUPLICATE_DEFAULT_ASSET","TWO_CURRENT_VERSIONS","LOCATOR_MIGRATION_MINTS_IDENTITY","SAME_PIXELS_MINTS_VERSION","CHANGED_PIXELS_REUSE_VERSION","VARIANT_AS_REVISION","MAP_EDGE_DISAGREEMENT","UNKNOWN_PORTAL_ENDPOINT","VERTICAL_FLATTENED_CARDINAL","RENDERER_INVENTS_TOPOLOGY","DYNAMIC_STATE_IN_ASSET","REVISIT_MINTS_NEW_ASSET","UNVERIFIED_CURRENT","PACK_EMBEDS_ASSET","STALE_LOCATOR_SEMANTIC_SUBSTITUTE","DIRECTION_FROM_FILENAME","VIEW_AS_FILE","GENERATED_PIXELS_MUTATE_TOPOLOGY"}
    assert required <= {case["mutation"] for case in cases}


def test_no_runtime_or_storage_backend_is_authorized_by_eval():
    doc = load_json(EVAL_PATH); serialized = json.dumps(doc, ensure_ascii=False)
    assert doc["status"] == "EXECUTABLE_CONFORMANCE_EVIDENCE_ONLY_NOT_AUTHORITY_EXTENSION"
    assert "runtime_implementation_authorized" not in doc
    assert all(name not in serialized.lower() for name in ("sqlite", "postgres", "redis"))
    assert doc["authority_boundary"]["external_pattern_evidence_authority"] == "INSPIRATION_ONLY_NOT_AWRSE_AUTHORITY"
