import android.support.test.runner.AndroidJUnit4;
import org.junit.*;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;
import android.support.test.InstrumentationRegistry;
import android.support.test.filters.SmallTest;
import cheap.hella.gobi.pybridge.PyBridge;
import cheap.hella.gobi.pybridge.PyBridgeProtos.Response;
import java.util.concurrent.Future;
import cheap.hella.gobi.pybridge.PyBridge;

@RunWith(AndroidJUnit4.class)
@SmallTest
public class PythonBridgeTest {

    @Before
    public void initPyBridge() {
        PyBridge.init(InstrumentationRegistry.getTargetContext());
    }
   
    @Test
    public void testUrlIsResolvable() {
        try {
            Future<Response.URLIsResolvableResponse> resFuture = 
                PyBridge.urlIsResolvable("https://www.youtube.com/watch?v=l_apnZ3DYOI");
            Response.URLIsResolvableResponse res = resFuture.get();
            assertTrue(res.getIsResolvable().getValue());
            assertEquals(res.getResolverNamesList().get(0).getValue(), "youtube");
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

}
