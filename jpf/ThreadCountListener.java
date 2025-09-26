package gov.nasa.jpf.listener;

import gov.nasa.jpf.vm.ThreadInfo;
import gov.nasa.jpf.vm.VM;
import gov.nasa.jpf.search.Search;
import gov.nasa.jpf.ListenerAdapter;

import java.util.HashSet;
import java.util.Set;

public class ThreadCountListener extends ListenerAdapter {
    private Set<String> uniqueThreadNames = new HashSet<>();

    @Override
    public void threadStarted(VM vm, ThreadInfo ti) {
        uniqueThreadNames.add(ti.getName());
    }

    @Override
    public void searchFinished(Search search) {
        System.out.println("Unique logical threads created during execution: "
                + (uniqueThreadNames.size() + 1));
    }
}