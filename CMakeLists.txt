cmake_minimum_required(VERSION 3.4.1)

set(PYTHON_HEADERS ${CMAKE_SOURCE_DIR}/src/main/includes/python/)
set(PYTHON_LIBS ${CMAKE_SOURCE_DIR}/src/main/libs/)
include_directories(${PYTHON_HEADERS})
include_directories(${PYTHON_LIBS})

add_library(
    pybridge
    SHARED
    src/main/jni/pybridge.c)

set(distribution_DIR ${CMAKE_CURRENT_SOURCE_DIR}/src/main/libs)
add_library(python2.7 SHARED IMPORTED)
set_target_properties(python2.7 PROPERTIES IMPORTED_LOCATION ${CMAKE_SOURCE_DIR}/src/main/libs/${ANDROID_ABI}/libpython2.7.so)

find_library(log-lib log)

target_link_libraries(
    pybridge
    python2.7
    android
    ${log-lib})
