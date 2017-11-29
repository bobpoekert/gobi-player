import android.app.Activity;
import android.os.Bundle;
import cheap.hella.gobi.pybridge.PyBridge;

public class TestActivity extends Activity {

    @Override
    public void onCreate(Bundle bundle) {
        PyBridge.init(this);
    }

    @Override
    public void onDestroy() {
        PyBridge.shutdown();
    }

}
