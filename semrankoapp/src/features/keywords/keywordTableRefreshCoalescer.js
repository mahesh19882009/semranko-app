export function createKeywordTableRefreshCoalescer(
  refreshTable,
  {
    debounceMs = 250,
    maxWaitMs = 1000,
    setTimer = setTimeout,
    clearTimer = clearTimeout,
    onError = () => {},
  } = {}
) {
  let disposed = false;
  let windowOpen = false;
  let pendingRefresh = false;
  let debounceTimer = null;
  let maxWaitTimer = null;
  let inFlight = null;
  let rerunAfterFlight = false;

  const clearDebounceTimer = () => {
    if (debounceTimer !== null) {
      clearTimer(debounceTimer);
      debounceTimer = null;
    }
  };

  const clearMaxWaitTimer = () => {
    if (maxWaitTimer !== null) {
      clearTimer(maxWaitTimer);
      maxWaitTimer = null;
    }
  };

  const runRefresh = () => {
    if (disposed) return;
    if (inFlight) {
      rerunAfterFlight = true;
      return;
    }

    inFlight = Promise.resolve()
      .then(refreshTable)
      .catch(onError)
      .finally(() => {
        inFlight = null;
        if (rerunAfterFlight && !disposed) {
          rerunAfterFlight = false;
          runRefresh();
        }
      });
  };

  const closeWindow = () => {
    debounceTimer = null;
    clearMaxWaitTimer();
    windowOpen = false;
    if (pendingRefresh) {
      pendingRefresh = false;
      runRefresh();
    }
  };

  const refreshDuringLongBurst = () => {
    maxWaitTimer = null;
    if (pendingRefresh) {
      pendingRefresh = false;
      runRefresh();
    }
  };

  const scheduleDebounce = () => {
    clearDebounceTimer();
    debounceTimer = setTimer(closeWindow, debounceMs);
  };

  const scheduleMaxWait = () => {
    if (maxWaitTimer === null) {
      maxWaitTimer = setTimer(refreshDuringLongBurst, maxWaitMs);
    }
  };

  return {
    request() {
      if (disposed) return;

      if (!windowOpen) {
        windowOpen = true;
        runRefresh();
      } else {
        pendingRefresh = true;
      }

      scheduleDebounce();
      scheduleMaxWait();
    },

    dispose() {
      disposed = true;
      pendingRefresh = false;
      rerunAfterFlight = false;
      clearDebounceTimer();
      clearMaxWaitTimer();
    },
  };
}
