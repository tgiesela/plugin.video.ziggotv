"""
Module containing the ziggo proxy service
"""
import xbmc

from resources.lib.servicemonitor import ServiceMonitor

if __name__ == '__main__':
    from resources.lib.utils import invoke_debugger
    invoke_debugger(False, 'vscode')

    MONITOR_SERVICE = ServiceMonitor()
    try:
        while not MONITOR_SERVICE.abortRequested():
            # Sleep/wait for abort for 5 seconds
            if MONITOR_SERVICE.waitForAbort(5):
                # Abort was requested while waiting. We should exit
                xbmc.log("MONITOR PROXYSERVICE WAITFORABORT timeout", xbmc.LOGDEBUG)
                break

    # pylint: disable=broad-exception-caught
    except Exception as exc:
        pass
    xbmc.log("STOPPING PROXYSERVICE", xbmc.LOGINFO)
    MONITOR_SERVICE.shutdown()
    xbmc.log("STOPPED PROXYSERVICE", xbmc.LOGINFO)
