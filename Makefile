VERSION		:= 0.1.0

LOCAL_EXEC_PATH	:= /usr/local/bin/ryzenm-limit/
LOCAL_SRC_PATH	:= /usr/local/src/ryzenm-limit/
LOCAL_LIB_PATH	:= /usr/local/lib/ryzenm-limit/

OPT_EXEC_PATH	:= /opt/ryzenm-limit/bin/
OPT_SRC_PATH	:= /opt/ryzenm-limit/src/
OPT_LIB_PATH	:= /opt/ryzenm-limit/lib/
OPT_CFG_PATH	:= /etc/opt/ryzenm-limit/

ROOT_CFG_PATH	:= /etc/ryzenm-limit/

PROJ_ROOT	:= $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PROJ_SRC_PATH	:= $(PROJ_ROOT)src/ryzenm_limit/

.PHONY: all

all:
	@echo -e "Please specify a target\nTargets can be reviewed inside $(PROJ_ROOT)Makefile"

# Valid targets below
install: local-install

local-install:
	mkdir -p $(LOCAL_SRC_PATH),$(LOCAL_LIB_PATH),$(ROOT_CONFIG_PATH)}
	cp $(PROJ_ROOT)ryzenm-limit $(LOCAL_EXEC_PATH)
	cp -r $(PROJ_SRC_PATH). $(LOCAL_SRC_PATH)
	cp $(PROJ_SRC_PATH)*.so $(LOCAL_LIB_PATH)
	cp -r $(PROJ_ROOT)config/. $(ROOT_CFG_PATH)

local-purge: local-uninstall
	rm -rf $(ROOT_CFG_PATH)

local-uninstall:
	rm $(LOCAL_EXEC_PATH)
	rm -rf $(LOCAL_SRC_PATH)
	rm -rf $(LOCAL_LIB_PATH)

opt-install:
	mkdir -p $(OPT_EXEC_PATH),$(OPT_SRC_PATH),$(OPT_LIB_PATH),$(OPT_CFG_PATH)}
	cp $(PROJ_ROOT)ryzenm-limit $(OPT_EXEC_PATH)
	cp -r $(PROJ_SRC_PATH). $(OPT_SRC_PATH)
	cp $(PROJ_SRC_PATH)*.so $(OPT_LIB_PATH)
	cp -r $(PROJ_ROOT)config/. $(OPT_CFG_PATH)

opt-purge: opt-uninstall
	rm -rf $(OPT_CFG_PATH)

opt-uninstall:
	rm $(OPT_EXEC_PATH)
	rm -rf $(OPT_SRC_PATH)
	rm -rf $(OPT_LIB_PATH)

# All pip installations assume that a virtual environment is setup
pip-install:
	python -m build
	python -m pip install --force $(PROJ_ROOT)dist/ryzenm_limit-$(VERSION)-py3-none-any.whl

pip-uninstall:
	python -m pip uninstall ryzenm_limit

pipx-install:
	python -m build
	pipx install --force $(PROJ_ROOT)dist/ryzenm_limit-$(VERSION)-py3-none-any.whl

pipx-uninstall:
	pipx uninstall ryzenm_limit

clean: clean-logs clean-dist

clean-logs:
	rm -r $(PROJ_ROOT)logs

clean-dist:
	rm -r $(PROJ_ROOT)dist
