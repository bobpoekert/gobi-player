#include <Python.h>
#include <jni.h>
#include <android.log>
#include <stdlib.h>

#define LOG(x) __android_log_write(ANDROID_LOG_INFO, "pybridge", (x))

PyObject *bootstrap_module;
PyObject *bootstrap_send; // function that inserts jobs into queue
PyObject *bootstrap_recv; // function that takes results from queue

/* --------------- */
/*   Android log   */
/* --------------- */

static PyObject *androidlog(PyObject *self, PyObject *args)
{
    char *str;
    if (!PyArg_ParseTuple(args, "s", &str))
        return NULL;

    LOG(str);
    Py_RETURN_NONE;
}



static PyMethodDef AndroidlogMethods[] = {
    {"log", androidlog, METH_VARARGS, "Logs to Android stdout"},
    {NULL, NULL, 0, NULL}
};


static struct PyModuleDef AndroidlogModule = {
    PyModuleDef_HEAD_INIT,
    "androidlog",        /* m_name */
    "Log for Android",   /* m_doc */
    -1,                  /* m_size */
    AndroidlogMethods    /* m_methods */
};


PyMODINIT_FUNC PyInit_androidlog(void)
{
    return PyModule_Create(&AndroidlogModule);
}


void setAndroidLog()
{
    input_queue = PyList_New(0);
    output_queue = PyList_New(0);
    
    // Inject  bootstrap code to redirect python stdin/stdout
    // to the androidlog module
    PyRun_SimpleString(
            "import sys\n" \
            "import androidlog\n" \
            "class LogFile(object):\n" \
            "    def __init__(self):\n" \
            "        self.buffer = ''\n" \
            "    def write(self, s):\n" \
            "        s = self.buffer + s\n" \
            "        lines = s.split(\"\\n\")\n" \
            "        for l in lines[:-1]:\n" \
            "            androidlog.log(l)\n" \
            "        self.buffer = lines[-1]\n" \
            "    def flush(self):\n" \
            "        return\n" \
            "sys.stdout = sys.stderr = LogFile()\n"
    );
}

#define JNIMETH(name) Java_org_schabi_newpipe_extractor_pybridge_PyBridge_ ## name


JNIEXPORT jint JNICALL JNIMETH(start)
        (JNIEnv *env, jclass jc, jstring path)
{
    LOG("Initializing the Python interpreter");

    jsize path_length = (*env)->GetStringUTFLength(env, path);

    // Get the location of the python files
    const char *pypath = (*env)->GetStringUTFChars(env, path, NULL);

    // Set Python paths
    wchar_t *wchar_paths = Py_DecodeLocale(pypath, NULL);
    Py_SetPath(wchar_paths);

    // Initialize Python interpreter and logging
    PyImport_AppendInittab("androidlog", PyInit_androidlog);
    Py_Initialize();
    setAndroidLog();

    // Bootstrap
    bootstrap_module = PyImport_ImportModule("boostrap");
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
