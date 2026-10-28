package com.delpalacio.picking;
import org.junit.Test;
import static org.junit.Assert.*;
public class MicRecoveryTest {
    @Test public void boundsRetriesAndResetsOnlyAfterStableRecording(){
        MicRecovery policy=new MicRecovery();
        for(long expected:new long[]{1000,2000,4000,8000,15000,-1,-1})assertEquals(expected,policy.nextDelayMillis());
        policy.stable();assertEquals(1000,policy.nextDelayMillis());
    }
}
