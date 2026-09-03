# 06 — Weapon Swap System

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Overview
Allow the player or AI to swap between multiple weapon meshes at runtime. Uses a variable to track the active weapon and swaps the StaticMesh on the Gun component.

## Endar Spire Correction
Recon on 2026-05-02 found player work should target `BP_TitanCharacter_P1`. The input system already has `IA_Swap` and `IA_SwapHold` under `/Game/FirstPerson/Input/Actions/`, mapped through `/Game/FirstPerson/Input/IMC_Default_Destiny` and `/Game/FirstPerson/Input/IMC_Weapons`. Do not create duplicate swap input or default mapping-context assets.

## Variables Needed
add_blueprint_variable blueprint_name: "BP_TitanCharacter_P1" variable_name: "ActiveWeaponIndex" variable_type: "Integer" default_value: "0"

add_blueprint_variable blueprint_name: "BP_TitanCharacter_P1" variable_name: "WeaponMeshes" variable_type: "Array"

## Swap Logic (Blueprint Graph)
create_node → InputAction node for IA_Swap (Triggered) create_node → Increment ActiveWeaponIndex, modulo WeaponMeshes.Length create_node → Get from WeaponMeshes array at ActiveWeaponIndex create_node → Set Static Mesh on the active weapon component to the retrieved mesh

## Input Action Setup
Use existing input action: `/Game/FirstPerson/Input/Actions/IA_Swap`

Use existing mapping context: `/Game/FirstPerson/Input/IMC_Default_Destiny`
