REPO_ROOT  := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
SCRIPTS    := $(REPO_ROOT)/scripts
PYTHONPATH := $(REPO_ROOT)/src

CASES    := $(wildcard ticket-*)
VARIANTS := 1 2 3 4 5

ALL := $(foreach c,$(CASES),$(foreach v,$(VARIANTS),$(c)/input.pick/$(v).xml))

.PHONY: all clean

all: $(ALL)

define PICK_RULE
$(1)/input.pick/$(2).xml:
	mkdir -p $(1)/input.pick
	PYTHONPATH=$(PYTHONPATH) $(SCRIPTS)/cherrypick_xml \
		--min-kb 0 --max-kb $(2) \
		$(1)/ \
		--output "input.pick/$(2).xml" \
		--verbose
endef

$(foreach c,$(CASES),$(foreach v,$(VARIANTS),$(eval $(call PICK_RULE,$(c),$(v)))))

clean:
	rm -rf $(foreach c,$(CASES),$(c)/input.pick)
