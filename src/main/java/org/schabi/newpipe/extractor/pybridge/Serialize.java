package org.schabi.newpipe.extractor.pybridge;

import java.util.Map;
import java.util.List;

import org.msgpack.core.MessagePack;
import org.msgpack.core.MessagePacker;
import org.msgpack.core.MessageUnpacker;
import org.msgpack.core.MessageBufferPacker;
import org.msgpack.value.Variable;

public class Serialize {


    public static byte[] serialize(Object v) {
        MessageBufferPacker packer = MessagePack.newDefaultBufferPacker();
        serialize(packer, v);
        packer.close();
        return packer.toByteArray();
    }

    static void serialize(MessageBufferPacker packer, String v) {
        packer.packString(v);
    }

    static void serialize(MessageBufferPacker packer, Integer v) {
        packer.packInt(v);
    }

    static void serialize(MessageBufferPacker packer, Long v) {
        packer.packLong(v);
    }

    static void serialize(MessageBufferPacker packer, Short v) {
        packer.packShort(v);
    }
    
    static void serialize(MessageBufferPacker packer, java.math.BigInteger v) {
        packer.packBigInteger(v);
    }
    
    static void serialize(MessageBufferPacker packer, Map v) {
        int size = v.size();
        packer.packMapHeader(size);
        for (Map.Entry e : v.entrySet()) {
            serialize(packer, e.getKey());
            serialize(packer, e.getValue());
        }
    }

    static void serialize(MessageBufferPacker packer, List v) {
        packer.packArrayHeader(v.size());
        for (Object e : v) {
            serialize(packer, e);
        }
    }

    static void serialize(MessageBufferPacker packer, Object v) {
        if (v == null) {
            packer.packNil();
        } else {
            throw new IllegalArgumentException();
        }
    }

    public static Variable deserialize(byte[] inp) {
        MessageUnpacker unpacker = MesagePack.newDefaultUnpacker(inp);
        return unpacker.unpackValue(new Variable());
    }

}
