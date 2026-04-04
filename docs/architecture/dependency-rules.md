# Dependency Rules

## Allowed Direction

- wrappers -> cli -> core packages -> contracts
- verification -> runtime-core / installer-core / contracts
- skill-catalog -> contracts

## Forbidden Direction

- wrappers owning install or runtime semantics
- runtime-core depending on generated distribution outputs
- installer-core depending on catalog internal topology
- generated files acting as authoritative inputs
