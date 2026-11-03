package com.delpalacio.picking;

final class ControlWorkflow {
    static final int FINISHED=0, START_FIRST=1, RESUME_FIRST=2, WAIT_FIRST=3,
        NEED_OTHER_CONTROLLER=4, START_SECOND=5, RESUME_SECOND=6, WAIT_SECOND=7;

    static int action(boolean firstExists, boolean firstDone, int firstUser,
                      boolean secondExists, boolean secondDone, int secondUser, int currentUser) {
        if (secondExists && secondDone) return FINISHED;
        if (!firstExists) return START_FIRST;
        if (!firstDone) return firstUser == currentUser ? RESUME_FIRST : WAIT_FIRST;
        if (firstUser == currentUser) return NEED_OTHER_CONTROLLER;
        if (!secondExists) return START_SECOND;
        return secondUser == currentUser ? RESUME_SECOND : WAIT_SECOND;
    }
}
