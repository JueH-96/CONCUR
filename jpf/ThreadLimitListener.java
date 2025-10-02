package gov.nasa.jpf.listener;

import gov.nasa.jpf.vm.ThreadInfo;
import gov.nasa.jpf.vm.ThreadList;
import gov.nasa.jpf.vm.VM;
import gov.nasa.jpf.search.Search;
import gov.nasa.jpf.ListenerAdapter;
import gov.nasa.jpf.Config;

public class ThreadLimitListener extends ListenerAdapter {

    private final int maxThreads;
    private boolean violationReported = false;
    private String violationMessage = "";

    public ThreadLimitListener(Config config) {
        this.maxThreads = config.getInt("threadlimitlistener.maxThreads", 5);
    }

    @Override
    public void threadStarted(VM vm, ThreadInfo ti) {
        int liveThreads = 0;
        ThreadList threads = vm.getThreadList();

        for (ThreadInfo t : threads) {
            if (t != null && t.isAlive()) {
                liveThreads++;
            }
        }

        if (liveThreads > maxThreads && !violationReported) {
            violationMessage = "ERROR: Too many threads! Current: " + liveThreads + ", Max allowed: " + maxThreads;
            System.out.println(violationMessage);

            violationReported = true;

            vm.getSearch().terminate();
            vm.breakTransition(violationMessage);
        }
    }

    @Override
    public void searchFinished(Search search) {
        if (violationReported) {
            System.out.println("====================================================== results");
            System.out.println(violationMessage);
            System.out.println("======================================================");
        }
    }
}
