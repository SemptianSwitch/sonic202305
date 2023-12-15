BFN_PLATFORM = bfnplatform_20230904_sai_1.11.0_deb11.deb
#$(BFN_PLATFORM)_URL = "https://github.com/barefootnetworks/sonic-release-pkgs/raw/dev/$(BFN_PLATFORM)"
$(BFN_PLATFORM)_URL = "http://192.168.3.23/proj/sonic/sde9.13.0/$(BFN_PLATFORM)"
SONIC_ONLINE_DEBS += $(BFN_PLATFORM)
$(BFN_SAI_DEV)_DEPENDS += $(BFN_PLATFORM)
