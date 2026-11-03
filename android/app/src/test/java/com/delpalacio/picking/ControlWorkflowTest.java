package com.delpalacio.picking;

import org.junit.Test;
import static org.junit.Assert.*;

public class ControlWorkflowTest {
    @Test public void firstControlCanStartResumeOrRemainReserved(){
        assertEquals(ControlWorkflow.START_FIRST,ControlWorkflow.action(false,false,0,false,false,0,10));
        assertEquals(ControlWorkflow.RESUME_FIRST,ControlWorkflow.action(true,false,10,false,false,0,10));
        assertEquals(ControlWorkflow.WAIT_FIRST,ControlWorkflow.action(true,false,11,false,false,0,10));
    }
    @Test public void secondControlRequiresAnotherPerson(){
        assertEquals(ControlWorkflow.NEED_OTHER_CONTROLLER,ControlWorkflow.action(true,true,10,false,false,0,10));
        assertEquals(ControlWorkflow.START_SECOND,ControlWorkflow.action(true,true,11,false,false,0,10));
        assertEquals(ControlWorkflow.RESUME_SECOND,ControlWorkflow.action(true,true,11,true,false,10,10));
        assertEquals(ControlWorkflow.WAIT_SECOND,ControlWorkflow.action(true,true,11,true,false,12,10));
        assertEquals(ControlWorkflow.FINISHED,ControlWorkflow.action(true,true,11,true,true,12,10));
    }
}
