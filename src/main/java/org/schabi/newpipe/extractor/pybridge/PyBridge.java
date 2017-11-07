package org.schabi.newpipe.extractor.pybridge;

import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import android.content.Context;
import android.app.Application;
import android.content.res.AssetManager;

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
        this.result = new CompletableFuture();
    }
    
    public byte[] serialize() {
        HashMap jobMap = new HashMap();
        jobMap.put("job_id", this.id);
        jobMap.put("job_args", this.input);
        return Serialize.serialize(jobMap);
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
    public AtomicBoolean running;

    public PyThread(AssetManager assetManager, LinkedBlockingQueue jobQueue) {
        this.jobQueue = jobQueue;
        this.assetManager = assetManager;
        this.pendingJobs = new HashMap<Integer,CompletableFuture>();
    }


    static Result deserializeResult(byte[] inp) {
        Variable v = Serialize.deserialize(inp);
        if (v.isMapValue()) {
            MapValue mv = v.asMapValue();
            Map<Value,Value> m = mv.map();
            Set<Value> keys = mv.keySet();
            
            int jobId = -1;
            Value value = null;

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

    public byte[] getJob() {
        Job res = this.jobQueue.poll();
        if (res == null) {
            return null;
        } else {
            return res.serialize();
        }
    }

    public boolean isRunning() {
        return this.running.get();
    }

    public void processResult(byte[] resultBlob) {
        if (resultBlob != null) {
            Result result = deserializeResult(resultBlob);
            CompletableFuture future = pendingJobs.get(result.id);
            if (future != null) {
                future.complete(result.value);
                pendingJobs.remove(result.id);
            }
        }
    }

    public void run() {
        this.running.set(true);
        try {
            PyBridge.run(this.assetManager, this);
        } finally {
            this.running.set(false);
        }
    }

    public void stop() {
        this.running.set(false);
    }

}

public class PyBridge {

     static native int run(AssetManager assetManager, PyThread thread);

     LinkedBlockingQueue jobQueue;
     PyThread runner;
     Thread pythonThread;
     AtomicInteger idCtr;

     static PyBridge instance = new PyBridge();

     PyBridge() {
         AssetManager assetManager;
         try {
             Application app = (Application) Class.forName("android.app.ActivityThread")
                 .getDeclaredMethod("currentApplication").invoke(null);
             assetManager = app.getApplicationContext().getAssets();
         } catch (Exception e) {
             throw new RuntimeException(e);
         }

         jobQueue = new LinkedBlockingQueue();
         runner = new PyThread(assetManager, jobQueue);
         pythonThread = new Thread(runner);
         idCtr = new AtomicInteger();
         pythonThread.start();
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

     Future doExec(Object argument) throws InterruptedException {
         Job job = new Job(newId(), argument);
         jobQueue.put(job);
         return job.result;
     }

     public static Future exec(Object argument) {
         return instance.exec(argument);
     }

}
