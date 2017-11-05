#include <Python.h>
#include <jni.h>
#include <android/log.h>
#include <asset_manager.h>
#include <stdlib.h>
#include "python_monkeypatches.h"

#define LOG(x) __android_log_write(ANDROID_LOG_INFO, "pybridge", (x))

PyObject *bootstrap_module;
PyObject *bootstrap_send; // function that inserts jobs into queue
PyObject *bootstrap_recv; // function that takes results from queue
AAssetManager *bootstrap_asset_manager;

static PyObject *androidlog(PyObject *self, PyObject *args)
{
    char *str;
    if (!PyArg_ParseTuple(args, "s", &str)) return 0;

    LOG(str);
    Py_RETURN_NONE;
}

static PyObject *load_asset(PyObject *self, PyObject *args) {

    char *filename;
    if (!PyArg_ParseTuple(args, "s", &filename)) return 0;
    if (!bootstrap_asset_manager) return 0;

    AAsset *asset = AAssetManager_open(bootstrap_asset_manager, filename, AASSET_MODE_STREAMING);
    off64_t asset_length = AAsset_getLength64(asset);

    PyObject *res = PyBuffer_New(asset_length);
    PyBuffer res_view;
    PyObject_GetBuffer(res, &res_view, PyBUF_WRITABLE);
    char *res_ptr = res_view.buf;
    size_t offset = 0;

    off64_t remaining = AAsset_getRemainingLength64(asset);
    size_t max_chunk_size = 1000 * 1024;

    while (offset < asset_length && remaining > 0) {
        size_t current_chunk_size;
        if ((asset_length - offset) >= remaining) {
            current_chunk_size = remaining;
        } else if (remaining > max_chunk_size) {
            current_chunk_size = max_chunk_size;
        } else {
            current_chunk_size = asset_length - offset;
        }

        char *chunk = res_ptr[offset];
        int bump = AAsset_read(asset, chunk, current_chunk_size);
        offset += bump;
    }

    AAsset_close(asset);

    return res;

}

static PyObject *asset_exists(PyObject *self, PyObject *args) {
    char *filename;
    if (!PyArg_ParseTuple(args, "s", &filename)) return 0;
    if (!bootstrap_asset_manager) return 0;


}

static PyMethodDef AndroidlogMethods[] = {
    {"log", androidlog, METH_VARARGS, "Logs to Android stdout"},
    {"load_asset", load_asset, METH_VARARGS, "Loads a file from dex assets and returns as a buffer"},
    {"asset_exists", asset_exists, METH_VARARGS, "Checks whether a dex asset file exists"}
    {NULL, NULL, 0, NULL}
};


static struct PyModuleDef AndroidlogModule = {
    PyModuleDef_HEAD_INIT,
    "androidbridge",        /* m_name */
    "Bridge into androidland",   /* m_doc */
    -1,                  /* m_size */
    AndroidlogMethods    /* m_methods */
};


PyMODINIT_FUNC PyInit_androidlog(void)
{
    return PyModule_Create(&AndroidlogModule);
}


void setAndroidLog()
{
    PyRun_SimpleString(python_monkeypatches);
}

#define JNIMETH(name) Java_org_schabi_newpipe_extractor_pybridge_PyBridge_ ## name


JNIEXPORT jint JNICALL JNIMETH(start)
        (JNIEnv *env, jclass jc, jobject asset_manager_obj)
{
    LOG("Initializing the Python interpreter");


    bootstrap_asset_manager = AAssetManager_fromJava(env, asset_manager_obj);
    

    // Initialize Python interpreter and logging
    PyImport_AppendInittab("androidlog", PyInit_androidlog);
    Py_Initialize();
    setAndroidLog();

    // Bootstrap
    bootstrap_module = PyImport_ImportModule("bootstrap");
    bootstrap_send = PyObject_GetAttrString(bootstrap_module, "send");
    bootstrap_recv = PyObject_GetAttrString(bootstrap_module, "recv");

    // Cleanup
    (*env)->ReleaseStringUTFChars(env, path, pypath);
    PyMem_RawFree(wchar_paths);

    return 0;
}

JNIEXPORT jint JNICALL JNIMETH(send)
    (JNIEnv *env, jclass jc, jbyteArray data)
{
    if (!bootstrap_send) return 0;

    jbyte *bytes = (*env)->GetByteArrayElements(env, data, 0);
    jsize array_length = (*env)->GetArrayLength(env, array);

    PyObject *py_buffer = PyBuffer_FromMemory(bytes, array_length);
    PyObject *py_arg_tuple = Py_BuildValue("(O)", py_buffer);
    PyObject_CallObject(bootstrap_send, py_arg_tuple);

    Py_DECREF(py_arg_tuple);
    Py_DECREF(py_buffer);
    (*env)->ReleaseByteArrayElements(env, data, 0);

    return 0;
}

JNIEXPORT jbyteArray JNICALL JNIMETH(recv)
    (JNIEnv *env, jclass jc)
{
    if (!bootstrap_recv) return 0;

    PyObject *result = PyObject_CallObject(bootstrap_recv, 0);
    if (PyObject_CheckBuffer(result)) {
        Py_buffer buf;
        if (!PyObject_GetBuffer(result, buf, 0)) {
            PyBuffer_Release(&buf);
            Py_DECREF(result);
            return 0;
        }
        jbyteArray res = (*env)->NewByteArray(env, buf.len);
        (*env)->SetByteArrayRegion(env, res, 0, buf.len, buf.buf);
        PyBuffer_Release(&buf);
        Py_DECREF(result);
        return res;
    } else {
        Py_DECREF(result);
        return 0;
    }

}

JNIEXPORT jint JNICALL JNIMETH(shutdown)
    (JNIEnv *env, jclass jc)
{
    LOG("python shutdown");
    Py_DECREF(bootstrap_recv);
    Py_DECREF(bootstrap_send);
    Py_DECREF(bootstrap_module);
    Py_Finalize();
    return 0;
}
