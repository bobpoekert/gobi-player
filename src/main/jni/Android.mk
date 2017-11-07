
execute_process(COMMAND python2.7 build.py)

# build libpybridge.so

include $(CLEAR_VARS)
LOCAL_MODULE := pybridge
LOCAL_SRC_FILES := pybridge.c
LOCAL_LDLIBS := -llog
LOCAL_SHARED_LIBRARIES := python2.7
include $(BUILD_SHARED_LIBRARY)

# include libpython2.7.so

include $(CLEAR_VARS)
LOCAL_PATH := $(call my-dir)
CRYSTAX_PATH := $ENV{ANDROID_HOME}/crystax-ndk
PYTHON_PATH := $(CRYSTAX_PATH)/sources/python/2.7
LOCAL_MODULE := python2.7
LOCAL_SRC_FILES := $(PYTHON_PATH)/libs/$(TARGET_ARCH_ABI)/libpython27.so
LOCAL_EXPORT_CFLAGS := -I $(PYTHON_PATH)/include/python/
include $(PREBUILT_SHARED_LIBRARY)
