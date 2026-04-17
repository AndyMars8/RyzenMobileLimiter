VERSION		:= 0.1.0

LOCAL_EXEC	:= /usr/local/bin/ryzenm-limit
LOCAL_SRC	:= /usr/local/src/ryzenm-limit/
LOCAL_LIB	:= /usr/local/lib/ryzenm-limit/

OPT_DIR		:= /opt/ryzenm-limit/
OPT_EXEC	:= /opt/ryzenm-limit/ryzenm-limit
OPT_SRC		:= /opt/ryzenm-limit/src/
OPT_LIB		:= /opt/ryzenm-limit/lib/
OPT_CFG		:= /etc/opt/ryzenm-limit/
OPT_SYSTEMD_P	:= \/opt\/ryzenm-limit\/ryzenm-limit start

ROOT_CFG	:= /etc/ryzenm-limit/

SYSTEMD_SVC	:= /etc/systemd/system/ryzenm-limit.service

PROJ_ROOT	:= $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PROJ_SRC	:= $(PROJ_ROOT)src/ryzenm_limit/
PROJ_SYSTEMD	:= $(PROJ_ROOT)systemd/ryzenm-limit.service

.PHONY: all

all:
	@echo -e "Please specify a target\nTargets can be reviewed inside $(PROJ_ROOT)Makefile"

# Valid targets below
install: local-install

uninstall: local-uninstall

purge: local-purge

local-install:
	mkdir -p {$(LOCAL_SRC),$(LOCAL_LIB),$(ROOT_CFG)}
	cp $(PROJ_ROOT)ryzenm-limit $(LOCAL_EXEC)
	cp -r $(PROJ_SRC). $(LOCAL_SRC)
	rm $(LOCAL_SRC)__*__.py
	mv $(LOCAL_SRC)*.so $(LOCAL_LIB)
	cp -r $(PROJ_ROOT)config/. $(ROOT_CFG)

local-uninstall:
	rm $(LOCAL_EXEC)
	rm -rf $(LOCAL_SRC)
	rm -rf $(LOCAL_LIB)

local-purge: local-uninstall rm-system-config

local-install-systemd: local-install
	cp $(PROJ_SYSTEMD) $(SYSTEMD_SVC)
	systemctl enable --now ryzenm-limit.service

local-uninstall-systemd: rm-systemd local-uninstall

local-purge-systemd: local-uninstall-systemd rm-system-config

opt-install:
	mkdir -p {$(OPT_SRC),$(OPT_LIB),$(OPT_CFG)}
	cp $(PROJ_ROOT)ryzenm-limit $(OPT_EXEC)
	cp -r $(PROJ_SRC). $(OPT_SRC)
	rm $(OPT_SRC)__*__.py
	mv $(OPT_SRC)*.so $(OPT_LIB)
	cp -r $(PROJ_ROOT)config/. $(OPT_CFG)

opt-uninstall:
	rm -rf $(OPT_DIR)

opt-purge: opt-uninstall rm-opt-config

opt-install-systemd: opt-install
	cp $(PROJ_SYSTEMD) $(PROJ_SYSTEMD).tmp
	sed -i "s/^\(ExecStart=\).*/\1$(OPT_SYSTEMD_P)/" $(PROJ_SYSTEMD).tmp
	mv $(PROJ_SYSTEMD).tmp $(SYSTEMD_SVC)
	systemctl enable --now ryzenm-limit.service

opt-uninstall-systemd: rm-systemd opt-uninstall

opt-purge-systemd: opt-uninstall-systemd rm-opt-config

rm-systemd:
	systemctl disable --now ryzenm-limit.service
	rm $(SYSTEMD_SVC)

rm-system-config:
	rm -rf $(ROOT_CFG)

rm-opt-config:
	rm -rf $(OPT_CFG)

# All pip installations assume that a virtual environment is set up
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
	rm -r ryzenm_limit.egg-info

clean-logs:
	rm -r $(PROJ_ROOT)logs

clean-dist:
	rm -r $(PROJ_ROOT)dist
