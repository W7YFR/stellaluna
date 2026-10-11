# Stellaluna workspace tasks. The other repos are checked out next to this one (make setup).
WS      := $(abspath ..)
KEYER   ?= $(WS)/k3ng_cw_keyer
ADAPTER := $(WS)/k3ng-vband-adapter
PRESET  ?= as-is

.DEFAULT_GOAL := help
.PHONY: help setup doctor schematics keyer-build keyer-matrix adapter-build

help:  ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'
	@echo "  options: KEYER=<checkout or worktree>  PRESET=<name>  ARGS='-D FEATURE_X ...'"

setup:  ## clone the keyer, adapter (and private vband) repos next to this one
	@tools/setup-workspace.sh

doctor:  ## check the workspace and build tools, with fixes for anything missing
	@tools/doctor.sh

schematics:  ## regenerate hardware/schematics.{html,md} and the SVGs
	@python3 hardware/schematic-gen/build_page.py >/dev/null && echo "schematics rebuilt"

keyer-build:  ## build the keyer (KEYER, PRESET, ARGS); never uploads
	@python3 tools/keyer-build/keyer-build.py --keyer "$(KEYER)" -p $(PRESET) $(ARGS)

keyer-matrix:  ## build every preset in tools/keyer-build/presets/matrix.txt (slow: when a feature is done)
	@python3 tools/keyer-build/keyer-build.py --keyer "$(KEYER)" --matrix --compare master $(ARGS)

adapter-build:  ## build the adapter firmware (USB environment); never uploads
	@cd "$(ADAPTER)" && pio run -e wemos_d1_mini32
