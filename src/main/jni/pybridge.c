#include <Python.h>
#include <jni.h>
#include <android/log.h>
#include <android/asset_manager.h>
#include <android/asset_manager_jni.h>
#include <stdlib.h>
#include "python_monkeypatches.h"

#define LOG(x) __android_log_write(ANDROID_LOG_INFO, "pybridge", (x))


static AAssetManager *bootstrap_asset_manager;
static jobject bootstrap_pythread;
static jclass boostrap_class;
static jmethodID boostrap_getJob_id;
static jmethodID boostrap_isRunning_id;
static jmethodID bootstrap_processResult_id;
static JNIEnv *bootstrap_jni_env;

static PyObject *androidlog(PyObject *self, PyObject *args) {
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

    if (asset_length < 1) {
        AAsset_close(asset);
        return 0;
    }

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

    PyBuffer_Release(&res_view);
    AAsset_close(asset);

    return res;

}

static PyObject *asset_filenames(PyObject *self, PyObject *args) {
    if (!bootstrap_asset_manager) return 0;

    AAssetDir *dir = AAssetManager_openDir(bootstrap_asset_manager, "org_schabi_newpipe_extractor_PyBridge");
    PyObject *res = PyList_New(0);

    char *current_fname = AAssetDir_getNextFilename(dir);
    while(current_fname) {
        PyList_Append(res, PyString_FromString(current_fname));
        current_fname = AAssetDir_getNextFilename(dir);
    }

    AAssetDir_close(dir);

    return res;

}

static PyObject *java_bytes_to_python(jbyteArray data) {
    jbyte *bytes = (*bootstrap_jni_env)->GetByteArrayElements(bootstrap_jni_env, data, 0);
    jsize array_length = (*bootstrap_jni_env)->GetArrayLength(bootstrap_jni_env, data);
    PyObject *res = PyBuffer_New(array_length);
    PyBuffer res_view;
    PyObject_GetBuffer(res, &res_view, PyBUF_WRITABLE);
    memcpy(res_view.buf, bytes, array_length);
    PyBuffer_Release(&res_view);
    (*bootstrap_jni_env)->ReleaseByteArrayElements(bootstrap_jni_env, data, JNI_ABORT);
    return res;
}

static jbyteArray python_to_java_bytes(PyObject *data) {
    Py_buffer buf_view;
    PyObject_GetBuffer(data, &buf_view, PyBUF_SIMPLE);

    jbyteArray res = (*bootstrap_jni_env)->NewByteArray(bootstrap_jni_env, size);
    (*bootstrap_jni_env)->SetByteArrayRegion(bootstrap_jni_env, res,
            0, buf_view.len, buf_view.buf);
    PyBuffer_Release(&buf_view);
    return res;
}

static PyObject *get_job(PyObject *self, PyObject *args) {
    jbyteArray arr = (*bootstrap_jni_env)->CallVoidMethod(
            bootstrap_jni_env, bootstrap_pythread, bootstrap_getJob_id);
    if (arr) {
        return java_bytes_to_python(arr);
    } else {
        Py_RETURN_NONE;
    }
}

static PyObject *is_running(PyObject *self, PyObject *args) {
    jboolean res = (*bootstrap_jni_env)->CallVoidMethod(
            bootstrap_jni_env, bootstrap_pythread, bootstrap_isRunning_id);
    if (res) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

static PyObject *process_result(PyObject *self, PyObject *args) {
    PyObject *result;
    if (!PyArg_ParseTuple(args, "O", &result)) return 0;

    jbyteArray arr = python_to_java_bytes(result);
    (*bootstrap_jni_env)->CallObjectMethod(
            bootstrap_jni_env, bootstrap_pythread, bootstrap_processResult_id, arr);

    Py_RETURN_NONE;
}

static PyMethodDef AndroidbridgeMethods[] = {
    {"log", androidlog, METH_VARARGS, "Logs to Android stdout"},
    {"load_asset", load_asset, METH_VARARGS, "Loads a file from dex assets and returns as a buffer"},
    {"asset_filenames", asset_filenames, METH_VARARGS, "Return a list of asset filenames"},
    {"get_job", get_job, METH_VARARGS, "Get the next job to run"},
    {"is_running", is_running, METH_VARARGS, "Returns whether python should continue running"},
    {"process_result", process_result, "Pass the result of a job back to java"},
    {NULL, NULL, 0, NULL}
};


static struct PyModuleDef AndroidbridgeModule = {
    PyModuleDef_HEAD_INIT,
    "androidbridge",        /* m_name */
    "Bridge into androidland",   /* m_doc */
    -1,                  /* m_size */
    AndroidbridgeMethods    /* m_methods */
};


PyMODINIT_FUNC PyInit_androidbridge(void)
{
    return PyModule_Create(&AndroidlogModule);
}

#define JNIMETH(name) Java_org_schabi_newpipe_extractor_pybridge_PyBridge_ ## name


JNIEXPORT jint JNICALL JNIMETH(run)
        (JNIEnv *env, jclass jc, jobject asset_manager_obj, jobject pythread)
{
    LOG("Initializing the Python interpreter");

    bootstrap_asset_manager = AAssetManager_fromJava(env, asset_manager_obj);

    bootstrap_pythread = pythread;
    bootstrap_jni_env = env;
    bootstrap_class = (*env)->GetObjectClass(env, pythread);
    bootstrap_getJob_id = (*env)->GetMethodID(env, bootstrap_class, "getJob", "()[B");
    bootstrap_isRunning_id = (*env)->GetMethodID(env, bootstrap_class, "isRunning", "()Z");
    bootstrap_processResult_id =
        (*env)->GetMethodID(env, bootstrap_class, "processResult", "([B)V");

    PyImport_AppendInittab("androidbridge", PyInit_androidbridge);
    Py_NoSiteFlag = 1;
    Py_SetProgramName("NewPipeExtractor");
    Py_Initialize();
    PyRun_SimpleString(python_monkeypatches);

    return 0;
}

JNIEXPORT jint JNICALL JNIMETH(send)
    (JNIEnv *env, jclass jc, jbyteArray data)
{
    if (!bootstrap_send) return 0;

    jbyte *bytes = (*env)->GetByteArrayElements(env, data, 0);
    jsize array_length = (*env)->GetArrayLength(env, data);

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
