# HaloUI Additions

# Face Unlock
TARGET_FACE_UNLOCK_SUPPORTED ?= $(TARGET_SUPPORTS_64_BIT_APPS)

ifeq ($(TARGET_FACE_UNLOCK_SUPPORTED),true)
PRODUCT_PACKAGES += \
    ParanoidSense

PRODUCT_SYSTEM_EXT_PROPERTIES += \
    ro.face.sense_service=true

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.biometrics.face.xml:$(TARGET_COPY_OUT_SYSTEM)/etc/permissions/android.hardware.biometrics.face.xml
endif

# Quick Tap
ifneq ($(TARGET_SUPPORTS_QUICK_TAP),false)
PRODUCT_PACKAGES += \
    ColumbusService
endif

# Kawase Blur
ifeq ($(TARGET_USES_KAWASE2_BLUR),true)
PRODUCT_SYSTEM_PROPERTIES += \
    debug.renderengine.blur_algorithm=kawase2
endif

# Packages
PRODUCT_PACKAGES += \
   GameSpace

# Updater
ifeq ($(BUILD_TYPE_OFFICIAL),true)
PRODUCT_PACKAGES += \
    Updater

PRODUCT_COPY_FILES += \
    vendor/lineage/prebuilt/common/etc/init/init.lineage-updater.rc:$(TARGET_COPY_OUT_SYSTEM_EXT)/etc/init/init.lineage-updater.rc
endif

# Enable Material Design 3 Expressive
PRODUCT_PRODUCT_PROPERTIES += is_expressive_design_enabled=true

# Inherit haloUI extras
include vendor/haloui/config.mk
