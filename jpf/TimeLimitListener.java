package gov.nasa.jpf.listener;
import gov.nasa.jpf.Config;
import gov.nasa.jpf.ListenerAdapter;
import gov.nasa.jpf.search.Search;

public class TimeLimitListener extends ListenerAdapter {
    private long startTime;
    private final long timeLimitMillis;

    public TimeLimitListener(Config config) {
        timeLimitMillis = config.getLong("timeLimitMillis", 900000);
    }


    @Override
    public void searchStarted(Search search) {
        startTime = System.currentTimeMillis();
    }

    @Override
    public void stateAdvanced(Search search) {
        long elapsed = System.currentTimeMillis() - startTime;
        if (elapsed > timeLimitMillis) {
            System.out.println("Time limit exceeded, terminating search...");
            search.terminate();
        }
    }
}
