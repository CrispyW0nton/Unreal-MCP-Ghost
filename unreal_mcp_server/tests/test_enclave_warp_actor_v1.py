from pathlib import Path


SOURCE_ROOT = Path(r"C:\UE\Enclave\Source\EnclaveProject")
HEADER = SOURCE_ROOT / "EnclaveWarpActor.h"
CPP = SOURCE_ROOT / "EnclaveWarpActor.cpp"


def test_warp_actor_exposes_authored_trigger_and_arrival_settings():
    header = HEADER.read_text(encoding="utf-8")
    assert "class ENCLAVEPROJECT_API AEnclaveWarpActor" in header
    assert "UBoxComponent" in header
    assert "DestinationLocation" in header
    assert "DestinationRotation" in header
    assert "ArrivalOffset" in header
    assert "CooldownSeconds" in header


def test_warp_actor_teleports_only_pawns_and_prevents_ping_pong():
    source = CPP.read_text(encoding="utf-8")
    assert "Cast<APawn>" in source
    assert "TeleportTo" in source
    assert "LastWarpTimes" in source
    assert "CooldownSeconds" in source
    assert "SetGenerateOverlapEvents(true)" in source


def test_warp_actor_preserves_player_control_orientation_when_authored():
    source = CPP.read_text(encoding="utf-8")
    assert "bApplyDestinationRotation" in source
    assert "Controller->SetControlRotation" in source
