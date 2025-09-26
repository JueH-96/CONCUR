package gov.nasa.jpf.listener;

import gov.nasa.jpf.ListenerAdapter;
import gov.nasa.jpf.vm.VM;
import gov.nasa.jpf.vm.ThreadInfo;
import gov.nasa.jpf.search.Search;

import java.util.HashMap;
import java.util.Map;

public class StarvationListener extends ListenerAdapter {

    private final Map<Integer, Long> lastRunStep = new HashMap<>();
    private final Map<Integer, Long> starvationSteps = new HashMap<>();
    private long stepCount = 0;

    @Override
    public void stateAdvanced(Search search) {
        stepCount++;

        VM vm = search.getVM();
        ThreadInfo[] threads = vm.getLiveThreads();

        ThreadInfo currentThread = vm.getCurrentThread();
        if (currentThread != null) {
            lastRunStep.put(currentThread.getId(), stepCount);
        }

        for (ThreadInfo ti : threads) {
            if (ti.isRunnable()) {
                long lastStep = lastRunStep.getOrDefault(ti.getId(), stepCount);
                long waitTime = stepCount - lastStep;
                starvationSteps.put(ti.getId(),
                        starvationSteps.getOrDefault(ti.getId(), 0L) + (waitTime > 0 ? 1 : 0));
            }
        }
    }

    @Override
    public void stateRestored(Search search) {
        stepCount--;
    }

    @Override
    public void searchFinished(Search search) {
        System.out.println("[JPF-STARVATION] search end，start concluding starvation...");
        for (Map.Entry<Integer, Long> entry : starvationSteps.entrySet()) {
            int threadId = entry.getKey();
            long waitSteps = entry.getValue();
            double waitRatio = (stepCount > 0) ? (double) waitSteps / stepCount : 0;

            if (waitRatio >= 1.0) {
                System.out.printf("[JPF-STARVATION] Thread ID: %d is starvation (waiting proportion: %.2f%%)%n",
                        threadId, waitRatio * 100);
            } else {
                System.out.printf("[JPF-STARVATION] Thread ID: %d OK (waiting proportion: %.2f%%)%n",
                        threadId, waitRatio * 100);
            }
        }
    }
}