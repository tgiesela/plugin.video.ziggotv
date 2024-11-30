"""
Module containing the ziggo proxy service
"""
import xbmc

from resources.lib.servicemonitor import ServiceMonitor

if __name__ == '__main__':
    from resources.lib.utils import invoke_debugger
    invoke_debugger(False, 'eclipse')

    monitor_service = ServiceMonitor()
    try:
        while not monitor_service.abortRequested():
            # Sleep/wait for abort for 5 seconds
            if monitor_service.waitForAbort(5):
                # Abort was requested while waiting. We should exit
                xbmc.log("MONITOR PROXYSERVICE WAITFORABORT timeout", xbmc.LOGINFO)
                break

    # pylint: disable=broad-exception-caught
    except Exception as exc:
        pass
    xbmc.log("STOPPING PROXYSERVICE", xbmc.LOGINFO)
    monitor_service.shutdown()
