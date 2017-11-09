package org.schabi.newpipe.extractor.pybridge;

import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.Map;
import java.util.Set;

import com.google.common.util.concurrent.SettableFuture;

import android.content.Context;
import android.app.Application;
import android.content.res.AssetManager;
import android.util.SparseArray;

import org.schabi.newpipe.extractor.pybridge.PyBridgeProtos.Request;
import org.schabi.newpipe.extractor.pybridge.PyBridgeProtos.Response;
import com.google.protobuf.InvalidProtocolBufferException;

abstract class Job<ResultType> {

    public SettableFuture<ResultType> result;
    public final int id;

    public Job(int id) {
        this.id = id;
        this.result = SettableFuture.create();
    }

    abstract void setRequest(Request.Builder b);

    public void complete(ResultType v) {
        this.result.set(v);
    }

    public byte[] serializeRequest() {
        Request.Builder builder = Request.newBuilder(); 
        builder.setJobId(this.id);
        this.setRequest(builder);

        return builder.build().toByteArray();
    }

}

class URLResolveJob extends Job<Response.URLResolveResponse> {

    String url;
    String username;
    String password;
    String resolverName;

    public URLResolveJob(int id, String url, String username, String password, String resolverName) {
        super(id);
        this.url = url;
        this.username = username;
        this.password = password;
        this.resolverName = resolverName;
    }

    @Override
    public void setRequest(Request.Builder b) {
        b.setUrlResolveRequest(Request.URLResolveRequest.newBuilder()
                .setUrl(this.url)
                .setUsername(this.username)
                .setPassword(this.password)
                .setResolverName(this.resolverName));
    }

}

class URLIsResolvableJob extends Job<Response.URLIsResolvableResponse> {

    String url;

    public URLIsResolvableJob(int id, String url) {
        super(id);
        this.url = url;
    }

    @Override
    void setRequest(Request.Builder b) {
        b.setUrlIsResolvableRequest(Request.URLIsResolvableRequest.newBuilder()
                .setUrl(this.url));
    }

}

class PyThread implements Runnable {

    LinkedBlockingQueue<Job> jobQueue;
    SparseArray<Job> pendingJobs;
    AssetManager assetManager; // IMPORTANT: this reference must be held as long as python is running
    AtomicBoolean running;

    public PyThread(AssetManager assetManager, LinkedBlockingQueue jobQueue) {
        this.jobQueue = jobQueue;
        this.assetManager = assetManager;
        this.pendingJobs = new SparseArray<Job>();
    }

    public byte[] getJob() {
        Job res = this.jobQueue.poll();
        if (res == null) {
            return null;
        } else {
            this.pendingJobs.put(res.id, res);
            return res.serializeRequest();
        }
    }

    public boolean isRunning() {
        return this.running.get();
    }

    public void processResult(byte[] resultBlob) {
        if (resultBlob != null) {
            Response response;
            try {
                response = Response.parseFrom(resultBlob);
            } catch (InvalidProtocolBufferException e) {
                throw new RuntimeException(e);
            }
            Integer id = Integer.valueOf((int) response.getJobId());
            Job job = pendingJobs.get(id);
            if (job != null) {
                job.complete(response);
                pendingJobs.remove(id);
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

     Future<Response.URLIsResolvableResponse> doUrlIsResolvable(String url) {
         try {
             URLIsResolvableJob job = new URLIsResolvableJob(newId(), url);
             jobQueue.put(job);
             return job.result;
         } catch (InterruptedException e) {
             throw new RuntimeException(e);
         }
     }

     public static Future<Response.URLIsResolvableResponse> urlIsResolvable(String url) {
         return instance.doUrlIsResolvable(url);
     }
     
     Future<Response.URLResolveResponse> doResolveUrl(
             String url,
             String username, String password,
             String resolver) {
         try {
             URLResolveJob job = new URLResolveJob(newId(), url, username, password, resolver);
             jobQueue.put(job);
             return job.result;
         } catch (InterruptedException e) {
             throw new RuntimeException(e);
         }
     }
     
     public static Future<Response.URLResolveResponse> resolveUrl(String url) {
         return instance.doResolveUrl(url, null, null, null);
     }
     
     public static Future<Response.URLResolveResponse> resolveUrl(String url, String username, String password) {
         return instance.doResolveUrl(url, username, password, null);
     }
     
     public static Future<Response.URLResolveResponse> resolveUrl(String url, String resolver) {
         return instance.doResolveUrl(url, null, null, resolver);
     }
     
     public static Future<Response.URLResolveResponse> resolveUrl(String url, String username, String password, String resolver) {
         return instance.doResolveUrl(url, username, password, resolver);
     }

}
