package org.schabi.newpipe.extractor.pybridge;

import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.AtomicInteger;
import java.util.HashMap;

import android.content.Context;

import org.msgpack.value.Variable;
import org.msgpack.value.Value;
import org.msgpack.value.MapValue;


class Job {

    public CompletableFuture result;
    public Object input;
    public final int id;

    public Job(int id, Object input) {
        this.input = input;
        this.id = id;
        this.result = new CompletableCompletableFuture();
    }

}

class Result {

    public final int id;
    public Value value;

    public Result(int id, Value value) {
        this.id = id;
        this.value = value;
    }

}

class PyThread implements Runnable {

    LinkedBlockingQueue<Job> jobQueue;
    HashMap<Integer,CompletableFuture> pendingJobs;
    AssetManager assetManager; // IMPORTANT: this reference must be held as long as python is running
    public synchronized boolean running;

    public PyThread(String datapath, LinkedBlockingQueue jobQueue, LinkedBlockingQueue resultQueue) {
        this.jobQueue = jobQueue;
        this.resultQueue = resultQueue;
        this.running = true;
        this.assetManager = assetManager;
        this.pendingJobs = new HashMap<Integer,CompletableFuture>();
    }

    static byte[] serialize(Job job) {
        HashMap jobMap = new HashMap();
        jobMap.put("job_id", job.id);
        jobMap.put("job_args", job.input);
        return Serialize.serialize(jobMap);
    }

    static Result deserializeResult(byte[] inp) {
        Variable v = Serialize.deserialize(inp);
        if (v.isMapValue()) {
            MapValue mv = v.asMapValue();
            Map<Value,Value> m = mv.map();
            Set<Value> keys = mv.keySet();
            
            int jobId;
            Value value;

            for (Value k : keys) {
                if (k.isStringValue()) {
                    String ks = k.asStringValue().asString();
                    if (ks.equals("job_id")) {
                        jobId = m.get(k).asIntegerValue().asInt();
                    } else if (ks.equals("value")) {
                        value = m.get(k);
                    }
                } 
            }

            return new Result(jobId, value);
        } else {
            return null;
        }
    }

    public void run() {
        PyBridge.start(this.assetManager);
        while(this.running) {
            Job job = this.jobQueue.poll(10, TimeUnit.MILLISECONDS);
            if (job != null) {
                pendingJobs.put(job.id, job.result);
                PyBridge.send(serialize(job));
            }

            byte[] resultBlob = PyBridge.recv();
            if (resultBlob != null) {
                Result result = deserializeResult(resultBlob);
                CompletableFuture future = pendingJobs.get(result.id);
                if (future != null) {
                    future.complete(result.value);
                    pendingJobs.remove(result.id);
                }
            }
        }
        PyBridge.shutdown();
    }

    public void stop() {
        this.running = false;
    }

}

public class PyBridge {

     static native int start(AssetManager assetManager);
     static native int shutdown();
     static native int send(byte[] data);
     static native byte[] recv();

     LinkedBlockingQueue jobQueue;
     PyThread runner;
     Thread pythonThread;
     AtomicInteger idCtr;

     static PyBdirge instance = new PyBridge();

     PyBridge() {
         Context context = Context.getApplicationContext();
         AssetManager assetManager = context.getAssets();

         jobQueue = new LinkedBlockingQueue();
         runner = new PyThread(pythonPath, jobQueue, resultQueue);
         pythonThread = new Thread(runner);
         idCtr = new AtomicInteger();
         pythonThread.start(assetManager);
     }

     int newId() {
         return this.idCtr.incrementAndGet();
     }

     void doShutdown() {
         this.runner.stop();
     }

     public static void shutdown() {
         instance.doShutdown();
     }

     Future doExec(Object argument) {
         Job job = new Job(newId(), argument);
         jobQueue.put(job);
         return job.result;
     }

     public static Future exec(Object argument) {
         return instance.exec(argument);
     }

}
