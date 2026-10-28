package com.delpalacio.picking;

/** A retry budget for recorder failures, never for silence or API writes. */
final class MicRecovery {
    private int failures;
    long nextDelayMillis(){return failures>=5?-1:Math.min(15000,1000L << failures++);}
    void stable(){failures=0;}
}
